# backend/src/celery/task_signals.py
"""
Celery signal hooks + sweeper for the preprocessing pipeline.
• Marks DB rows IN_PROGRESS / COMPLETED / FAILED in real‑time
• Adds human‑readable messages when the worker crashes
• Periodically fails orphaned file tasks and updates their parent task
• Broadcasts task updates via WebSocket for real-time frontend updates
"""

from __future__ import annotations

import datetime
import logging

from celery import signals
from celery.exceptions import SoftTimeLimitExceeded, WorkerLostError

from .. import models
from ..dependencies import get_db
from .celery_config import celery_app

logger = logging.getLogger(__name__)


# ────────────────── helpers ──────────────────
def _update(
    task_db_id: int,
    status: models.PreprocessingStatus,
    message: str | None = None,
    broadcast: bool = False,
    event: str | None = None,
):
    """Safely update the PreprocessingTask row and associated file tasks."""
    with next(get_db()) as db:  # type: Session
        task = db.get(models.PreprocessingTask, task_db_id)
        if not task:
            return

        # If failing the parent task, also fail all pending/in-progress file tasks
        if status == models.PreprocessingStatus.FAILED:
            now = datetime.datetime.now(datetime.UTC)
            for ft in task.file_tasks:
                if ft.status in (
                    models.PreprocessingStatus.PENDING,
                    models.PreprocessingStatus.IN_PROGRESS,
                ):
                    ft.status = models.PreprocessingStatus.FAILED
                    ft.error_message = message or "Parent task failed"
                    ft.completed_at = now

        task.status = status
        if message:
            task.message = message
        if status in (
            models.PreprocessingStatus.COMPLETED,
            models.PreprocessingStatus.FAILED,
        ):
            task.completed_at = datetime.datetime.now(datetime.UTC)
        db.commit()

        if broadcast:
            # Determine event type based on status if not provided
            if event is None:
                if status == models.PreprocessingStatus.FAILED:
                    event = "failed"
                elif status == models.PreprocessingStatus.COMPLETED:
                    event = "completed"
                else:
                    event = "progress"
            _broadcast_preprocessing_update(task, event)


def _broadcast_preprocessing_update(
    task: models.PreprocessingTask, event: str = "progress"
):
    """Broadcast preprocessing task update via Redis pub/sub.

    Since Celery workers run in separate processes/containers from FastAPI,
    we use Redis pub/sub to send messages to the FastAPI backend, which then
    broadcasts to connected WebSocket clients.
    """
    try:
        from ..utils.redis_broadcast import publish_task_update

        message = {
            "type": "preprocessing_update",
            "task_id": task.id,
            "project_id": task.project_id,
            "status": task.status,
            "processed_files": task.processed_files,
            "total_files": task.meta.get("total_files", 0) if task.meta else 0,
            "failed_files": task.failed_files,
            "cancelled_files": task.skipped_files,
            "configuration_name": task.configuration.name
            if task.configuration
            else None,
            "event": event,
        }

        if not publish_task_update(message):
            logger.warning("Failed to publish preprocessing update via Redis")
    except ImportError as e:
        logger.debug("Redis broadcast not available: %s", e)
    except Exception as e:
        logger.error(f"Error broadcasting preprocessing update: {e}")


def _broadcast_trial_update(trial: models.Trial, event: str):
    """Broadcast trial task update via Redis pub/sub.

    Since Celery workers run in separate processes/containers from FastAPI,
    we use Redis pub/sub to send messages to the FastAPI backend, which then
    broadcasts to connected WebSocket clients.
    """
    try:
        from ..utils.redis_broadcast import publish_trial_update

        message = {
            "type": "trial_update",
            "trial_id": trial.id,
            "project_id": trial.project_id,
            "status": trial.status.value
            if hasattr(trial.status, "value")
            else str(trial.status),
            "docs_done": trial.docs_done,
            "documents_count": len(trial.document_ids) if trial.document_ids else 0,
            "progress": float(trial.progress) if trial.progress else 0,
            "name": trial.name,
            "event": event,
        }

        if not publish_trial_update(message):
            logger.warning("Failed to publish trial update via Redis")
    except ImportError as e:
        logger.debug("Redis broadcast not available: %s", e)
    except Exception as e:
        logger.error(f"Error broadcasting trial update: {e}")


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
    """Convert raw Celery errors into user‑friendly messages and broadcast via WebSocket."""
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

    _update(args[0], models.PreprocessingStatus.FAILED, friendly, broadcast=True)


# ────────────────── periodic sweeper ──────────────────
def sweep_orphans():
    cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=30)
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
                f"{completed} of {total} files processed successfully, "
                f"{failed} failed (worker crashed or was killed)."
            )
            parent.completed_at = datetime.datetime.now(datetime.UTC)

        db.commit()

        # 3) broadcast updates for affected parent tasks
        for pid in parent_ids:
            parent = db.get(models.PreprocessingTask, pid)
            if parent:
                _broadcast_preprocessing_update(parent, "failed")

        # 4) fail stuck Trials. The extraction heartbeat bumps `updated_at` every
        # few seconds, so a PROCESSING trial whose `updated_at` is older than the
        # cutoff has a dead worker (crash / OOM / SIGKILL) — the top-level
        # try/except in extract_info_celery only catches exceptions, not a hard
        # worker kill, so without this the trial would stay PROCESSING forever.
        trial_cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            minutes=10
        )
        stuck_trials = (
            db.query(models.Trial)
            .filter(
                models.Trial.status == models.TrialStatus.PROCESSING,
                models.Trial.updated_at < trial_cutoff,
            )
            .all()
        )
        for trial in stuck_trials:
            trial.status = models.TrialStatus.FAILED
            trial.finished_at = datetime.datetime.now(datetime.UTC)
            trial.meta = (trial.meta or {}) | {
                "failures": {"_sweeper": "Marked FAILED by sweeper (worker lost)"},
                "eta_seconds": 0,
            }
            affected += 1
        db.commit()

        for trial in stuck_trials:
            _broadcast_trial_update(trial, "failed")

    return f"{affected} orphaned file tasks / stuck trials marked as FAILED"


# Register the sweeper as a periodic Celery task. Guarded so the module can be
# imported even when Celery is disabled (celery_app is None) — e.g. in tests or
# DISABLE_CELERY mode. Under normal operation this module is imported inside
# celery_config's `if not DISABLE_CELERY` block, where celery_app is set.
if celery_app is not None:
    sweep_orphans = celery_app.task(
        name="backend.src.celery.task_signals.sweep_orphans"
    )(sweep_orphans)

    @celery_app.on_after_configure.connect
    def _setup_sweeper(sender, **_):
        """Register the periodic orphan sweeper (every 5 minutes)."""
        sender.add_periodic_task(
            300,  # seconds
            sweep_orphans.s(),
            name="sweep_orphaned_file_tasks",
        )
