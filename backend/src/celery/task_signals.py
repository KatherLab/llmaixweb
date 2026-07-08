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
from sqlalchemy import func

from .. import models
from ..dependencies import get_db
from .celery_config import celery_app

logger = logging.getLogger(__name__)

# How long to wait between (re)subscription attempts for the
# settings-invalidation channel when Redis is unavailable or the connection
# drops. Keeps the listener alive so a recovering Redis is picked up without
# a worker restart.
_SETTINGS_SUBSCRIBE_RETRY_SECONDS = 30.0


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
            "project_trial_number": trial.project_trial_number,
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
    if sender is None or not _is_preprocess_task(sender.name):
        return
    if not args:
        return
    # Don't resurrect a task that's already terminal. With task_acks_late=True
    # and a Redis visibility_timeout, a message can be re-delivered after the
    # original run (or the sweeper below) already finalized this task as
    # COMPLETED/FAILED/CANCELLED. Flipping it back to IN_PROGRESS here would
    # let the task body's stale-check then mark a COMPLETED task FAILED. The
    # task body still re-checks and bails on terminal status, but we avoid the
    # transient wrong state (and a misleading progress broadcast) entirely.
    with next(get_db()) as db:
        task = db.get(models.PreprocessingTask, args[0])
        if not task:
            return
        if task.status in (
            models.PreprocessingStatus.COMPLETED,
            models.PreprocessingStatus.FAILED,
            models.PreprocessingStatus.CANCELLED,
        ):
            return
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
    if sender is None or not _is_preprocess_task(sender.name):
        return
    if not args:
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
    # A file task whose last heartbeat (falling back to started_at for rows
    # that never heartbeated — e.g. created before the heartbeat column
    # existed, or crashed before the first bump) is older than this window is
    # assumed to have a dead worker. The pipeline heartbeats every ~15s while
    # actively processing, so 10 minutes is a generous margin that won't reap
    # slow-but-legitimate files even when their per-file timeout (up to 2h)
    # exceeds the window.
    cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=10)
    with next(get_db()) as db:
        # 1) fail orphaned file tasks
        q = db.query(models.FilePreprocessingTask).filter(
            models.FilePreprocessingTask.status.in_(
                [
                    models.PreprocessingStatus.PENDING,
                    models.PreprocessingStatus.IN_PROGRESS,
                ]
            ),
            func.coalesce(
                models.FilePreprocessingTask.last_heartbeat_at,
                models.FilePreprocessingTask.started_at,
            )
            < cutoff,
        )
        affected = 0
        parent_ids: set[int] = set()

        for ft in q.all():
            ft.status = models.PreprocessingStatus.FAILED
            ft.error_message = "Marked FAILED by sweeper (worker lost)"
            affected += 1
            parent_ids.add(ft.preprocessing_task_id)

        db.commit()

        # 2) refresh parent tasks so their summary & message are accurate.
        # Only finalize a parent here when it has NO file tasks still in
        # flight — otherwise marking it FAILED now would flap back to
        # COMPLETED once the still-running files finish on a live worker.
        # Count failures explicitly so CANCELLED files aren't miscounted as
        # failed (the old `failed = total - completed` counted every non-
        # completed status, including CANCELLED and still-running, as failed).
        in_flight_statuses = (
            models.PreprocessingStatus.PENDING,
            models.PreprocessingStatus.IN_PROGRESS,
        )
        finalized_parent_ids: set[int] = set()
        for pid in parent_ids:
            parent = db.get(models.PreprocessingTask, pid)
            if not parent:
                continue

            file_tasks = parent.file_tasks
            total = len(file_tasks)
            completed = sum(
                1
                for ft in file_tasks
                if ft.status == models.PreprocessingStatus.COMPLETED
            )
            failed = sum(
                1 for ft in file_tasks if ft.status == models.PreprocessingStatus.FAILED
            )
            in_flight = sum(1 for ft in file_tasks if ft.status in in_flight_statuses)

            # Keep the persisted counters current regardless.
            parent.processed_files = completed
            parent.failed_files = failed

            if in_flight > 0:
                # Some files are still being processed by a live worker; leave
                # the parent's status alone and let the normal completion path
                # set the final FAILED/COMPLETED tally once they finish.
                continue

            finalized_parent_ids.add(pid)
            parent.status = models.PreprocessingStatus.FAILED
            parent.message = (
                f"{completed} of {total} files processed successfully, "
                f"{failed} failed (worker crashed or was killed)."
            )
            parent.completed_at = datetime.datetime.now(datetime.UTC)

        db.commit()

        # 3) broadcast updates for parents we actually finalized. Parents with
        # files still in flight are left untouched (no status flap).
        for pid in finalized_parent_ids:
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
    sweep_orphans_task = celery_app.task(
        name="backend.src.celery.task_signals.sweep_orphans"
    )(sweep_orphans)

    @celery_app.on_after_configure.connect
    def _setup_sweeper(sender, **_):
        """Register the periodic orphan sweeper (every 5 minutes)."""
        sender.add_periodic_task(
            300,  # seconds
            sweep_orphans_task.s(),
            name="sweep_orphaned_file_tasks",
        )

    # ────────────────── runtime-settings propagation ──────────────────
    # Each Celery worker process keeps its own @lru_cache'd copy of the
    # settings (see core/dynamic_settings.py). When an admin changes a
    # setting in the web process, reload_settings_cache() publishes an
    # invalidation message; this subscriber, started once per worker process,
    # receives it and reloads the local cache. Without it, worker config is
    # stale until process restart (e.g. an OCR engine disabled for privacy
    # would keep running in workers).
    def _settings_invalidation_listener() -> None:
        import json
        import threading

        from ..utils.redis_broadcast import subscribe_settings_invalidate

        def _loop():
            # Retry the subscription: if Redis is unavailable at worker start
            # (or drops mid-run), re-attempt periodically so a Redis that comes
            # back online is picked up without a worker restart. Previously a
            # single None from subscribe_settings_invalidate() aborted the
            # listener for the life of the process.
            pubsub = None
            while True:
                pubsub = subscribe_settings_invalidate()
                if pubsub is None:
                    import time

                    time.sleep(_SETTINGS_SUBSCRIBE_RETRY_SECONDS)
                    continue
                logger.info("Subscribed to settings-invalidation channel")
                try:
                    while True:
                        # Blocking get_message with a timeout so the thread can
                        # react to messages without busy-looping.
                        message = pubsub.get_message(timeout=5.0)
                        if message and message.get("type") == "message":
                            try:
                                data = json.loads(message["data"])
                            except Exception:
                                data = {}
                            if data.get("type") == "settings_invalidate":
                                try:
                                    from ..core.dynamic_settings import (
                                        reload_settings_cache,
                                    )

                                    # broadcast=False: this is the receiving
                                    # side; don't re-publish (avoids a loop).
                                    reload_settings_cache(broadcast=False)
                                    logger.info(
                                        "Reloaded settings cache after "
                                        "invalidation broadcast"
                                    )
                                except Exception as e:
                                    logger.error(
                                        "Failed to reload settings cache: %s",
                                        e,
                                        exc_info=True,
                                    )
                except Exception as e:
                    logger.warning("Settings invalidation listener disconnected: %s", e)
                finally:
                    try:
                        pubsub.unsubscribe()
                        pubsub.close()
                    except Exception:
                        pass
                # Connection lost — loop and re-subscribe.
                import time

                time.sleep(_SETTINGS_SUBSCRIBE_RETRY_SECONDS)

        # Daemon so it never blocks process shutdown.
        threading.Thread(
            target=_loop, name="settings-invalidate-sub", daemon=True
        ).start()

    @signals.worker_process_init.connect
    def _start_settings_listener(**_):
        """Start the settings-invalidation subscriber per worker process."""
        _settings_invalidation_listener()
