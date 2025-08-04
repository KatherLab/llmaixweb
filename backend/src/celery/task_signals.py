# backend/src/celery/task_signals.py
"""
Celery signal hooks + sweeper for the preprocessing pipeline.
• Marks DB rows IN_PROGRESS / COMPLETED / FAILED in real‑time
• Adds human‑readable messages when the worker crashes
• Periodically fails orphaned file tasks and updates their parent task
"""

from __future__ import annotations

import datetime

from celery import signals
from celery.exceptions import SoftTimeLimitExceeded, WorkerLostError

from .. import models
from ..dependencies import get_db
from .celery_config import celery_app


# ────────────────── helpers ──────────────────
def _update(
    task_db_id: int, status: models.PreprocessingStatus, message: str | None = None
):
    """Safely update the PreprocessingTask row."""
    with next(get_db()) as db:  # type: Session
        task = db.get(models.PreprocessingTask, task_db_id)
        if not task:
            return
        task.status = status
        if message:
            task.message = message
        if status in (
            models.PreprocessingStatus.COMPLETED,
            models.PreprocessingStatus.FAILED,
        ):
            task.completed_at = datetime.datetime.now(datetime.UTC)
        db.commit()


def _is_preprocess_task(sender_name: str) -> bool:
    """True for the heavy preprocessing tasks only."""
    return sender_name.endswith("process_files_async") or sender_name.endswith(
        "preprocess_file_celery"
    )


# ────────────────── Celery signal handlers ──────────────────
@signals.task_prerun.connect
def mark_started(sender=None, task_id=None, args=None, **_):
    if _is_preprocess_task(sender.name):
        _update(args[0], models.PreprocessingStatus.IN_PROGRESS)


# @signals.task_postrun.connect
# def mark_done(sender=None, task_id=None, retval=None, args=None, **_):
#
#     if _is_preprocess_task(sender.name):
#         _update(args[0], models.PreprocessingStatus.COMPLETED)
#         print("mark_done")


@signals.task_failure.connect
def mark_failed(sender=None, task_id=None, exception=None, args=None, **_):
    """Convert raw Celery errors into user‑friendly messages."""
    if not _is_preprocess_task(sender.name):
        return

    if isinstance(exception, WorkerLostError):
        friendly = (
            "The worker process crashed while preprocessing. "
            "This usually means the machine ran out of memory or a native "
            "library (e.g. PaddleOCR) seg‑faulted. "
            "Please check the Celery worker logs."
        )
    elif isinstance(exception, SoftTimeLimitExceeded):
        friendly = "Preprocessing exceeded the maximum runtime limit."
    else:
        friendly = str(exception) or "Preprocessing task failed with an unknown error."

    _update(args[0], models.PreprocessingStatus.FAILED, friendly)


# ────────────────── periodic sweeper ──────────────────
@celery_app.on_after_configure.connect
def _setup_sweeper(sender, **_):
    """
    Every 5 minutes:
      • mark any FilePreprocessingTask stuck in PENDING/IN_PROGRESS
        for >30 min as FAILED
      • update counters + message on their parent PreprocessingTask
    """
    sender.add_periodic_task(
        300,  # seconds
        sweep_orphans.s(),
        name="sweep_orphaned_file_tasks",
    )


@celery_app.task
def sweep_orphans():
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
    with next(get_db()) as db:
        # 1) fail orphaned file tasks
        q = db.query(models.FilePreprocessingTask).filter(
            models.FilePreprocessingTask.status.in_(
                [
                    models.PreprocessingStatus.PENDING,
                    models.PreprocessingStatus.IN_PROGRESS,
                ]
            ),
            models.FilePreprocessingTask.started_at < cutoff,
        )
        affected = 0
        parent_ids: set[int] = set()

        for ft in q.all():
            ft.status = models.PreprocessingStatus.FAILED
            ft.error_message = "Marked FAILED by sweeper (worker lost)"
            affected += 1
            parent_ids.add(ft.preprocessing_task_id)

        db.commit()

        # 2) refresh parent tasks so their summary & message are accurate
        for pid in parent_ids:
            parent = db.get(models.PreprocessingTask, pid)
            if not parent:
                continue

            total = len(parent.file_tasks)
            completed = sum(
                1
                for ft in parent.file_tasks
                if ft.status == models.PreprocessingStatus.COMPLETED
            )
            failed = total - completed

            parent.status = models.PreprocessingStatus.FAILED
            parent.processed_files = completed
            parent.failed_files = failed
            parent.message = (
                f"{completed}of{total} files processed successfully, "
                f"{failed} failed (worker crashed or was killed)."
            )
            parent.completed_at = datetime.datetime.now(datetime.UTC)

        db.commit()

    return f"{affected} orphaned file tasks marked as FAILED"
