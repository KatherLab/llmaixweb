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
from sqlalchemy import func

from .. import models
from ..core.config import settings
from ..dependencies import get_db
from ..middleware.error_handlers import (
    internal_error_message,
    operational_error_message,
)
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


@signals.task_prerun.connect
def mark_trial_started(sender=None, task_id=None, args=None, kwargs=None, **_):
    """Flip a queued Trial to PROCESSING the moment a worker actually starts it.

    Trials are created PENDING for the Celery path (see create_trial) and only
    become PROCESSING here. This is what makes the orphan sweeper safe: it fails
    PROCESSING trials whose ``updated_at`` is stale, so a trial that is merely
    waiting in the queue behind busy workers (still PENDING) is never falsely
    swept to FAILED. Skips terminal trials (e.g. cancelled while queued) so a
    re-delivery can't resurrect them, mirroring ``mark_started`` above.
    """
    if sender is None or not sender.name.endswith("extract_info_celery"):
        return
    trial_id = (kwargs or {}).get("trial_id")
    if trial_id is None and args:
        trial_id = args[0]
    if trial_id is None:
        return
    with next(get_db()) as db:
        trial = db.get(models.Trial, trial_id)
        if not trial:
            return
        if trial.status in (
            models.TrialStatus.COMPLETED,
            models.TrialStatus.FAILED,
            models.TrialStatus.CANCELLED,
        ):
            return
        trial.status = models.TrialStatus.PROCESSING
        if trial.started_at is None:
            trial.started_at = datetime.datetime.now(datetime.UTC)
        db.commit()


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

    # Record the real cause (WorkerLostError → OOM/segfault, SoftTimeLimitExceeded
    # → runtime cap, or any other worker-side exception) under a correlation id in
    # the error log, and surface only a generic message + that id to the user —
    # never the raw exception text or internal infrastructure hints. The exception
    # type stored in the log tells an admin whether it was a crash, timeout, etc.
    friendly = internal_error_message(
        exception,
        prefix="Preprocessing failed before it could complete. Please retry.",
    )

    _update(args[0], models.PreprocessingStatus.FAILED, friendly, broadcast=True)


# ────────────────── periodic sweeper ──────────────────
def sweep_orphans():
    # A file task whose last heartbeat (falling back to started_at for rows
    # that never heartbeated — e.g. created before the heartbeat column
    # existed, or crashed before the first bump) is older than this window is
    # assumed to have a dead worker. The pipeline heartbeats every ~15s while
    # actively processing, so ORPHAN_STALE_SECONDS (default 120s = 8+ missed
    # heartbeats) won't reap slow-but-legitimate files even when their per-file
    # timeout (up to 2h) exceeds the window. A *restart* is handled instantly by
    # the worker-startup reclaim below; this sweeper is the backstop for a
    # crashed-but-not-restarted worker (OOM/segfault) and multi-worker setups.
    cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
        seconds=settings.ORPHAN_STALE_SECONDS
    )
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

        # Generic user-facing text (no "sweeper/worker lost" infra detail); the
        # real cause is recorded once per finalized parent below, and its error
        # id is carried on the parent's message.
        for ft in q.all():
            ft.status = models.PreprocessingStatus.FAILED
            ft.error_message = (
                "Preprocessing was interrupted before it completed. Please retry."
            )
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
            # Keep the factual counts (not sensitive), but move the "worker
            # crashed/lost" cause into the error log and expose only its id.
            parent.message = operational_error_message(
                detail=(
                    f"PreprocessingTask {pid} finalized by orphan sweeper "
                    f"(worker crashed or was killed): {failed} of {total} file "
                    f"tasks failed, {completed} completed."
                ),
                prefix=(
                    f"{completed} of {total} files processed successfully, "
                    f"{failed} failed."
                ),
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
            seconds=settings.ORPHAN_STALE_SECONDS
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
                "failures": {
                    "_sweeper": operational_error_message(
                        detail=(
                            f"Trial {trial.id} finalized by orphan sweeper "
                            "(worker crashed or was killed)."
                        ),
                        prefix="The trial was interrupted before it completed. Please retry.",
                    )
                },
                "eta_seconds": 0,
            }
            affected += 1
        db.commit()

        for trial in stuck_trials:
            _broadcast_trial_update(trial, "failed")

    if affected == 0:
        return "no orphaned file tasks / stuck trials found"
    return f"{affected} orphaned file tasks / stuck trials marked as failed"


# ────────────────── worker-startup reclaim ──────────────────
def reclaim_orphaned_on_startup(role: str) -> str:
    """Immediately finalize work a just-restarted worker abandoned.

    The time-based ``sweep_orphans`` can't react to a *restart* — a benign
    ``docker compose restart`` kills the worker mid-task, and with
    ``task_acks_late`` the in-flight Celery message is stranded in the broker's
    unacked set behind the 8h ``visibility_timeout`` (it is NOT re-queued for
    hours). Meanwhile the DB row sits IN_PROGRESS/PROCESSING and the UI shows a
    dead-looking spinner until the staleness window elapses.

    A freshly booted worker knows for certain that anything still non-terminal
    in the queue(s) it serves was interrupted, so we finalize it as FAILED right
    now (the user retries). Scoped by ``role`` so a default-worker restart never
    touches a live preprocess worker's in-flight files, and vice-versa — the
    stock deployment runs exactly one worker per role. In a scaled multi-worker
    deployment (several workers on the same queue) leave ``CELERY_WORKER_ROLE``
    unset so this is skipped and the staleness sweeper handles recovery instead.
    """
    now = datetime.datetime.now(datetime.UTC)
    reclaimed = 0

    with next(get_db()) as db:
        if role == "preprocess":
            tasks = (
                db.query(models.PreprocessingTask)
                .filter(
                    models.PreprocessingTask.status
                    == models.PreprocessingStatus.IN_PROGRESS
                )
                .all()
            )
            finalized_ids: list[int] = []
            for task in tasks:
                # Record the "worker restarted" cause in the error log under a
                # fresh id (one per task); the user sees only a generic message
                # plus that id, never the internal restart detail.
                msg = operational_error_message(
                    detail=(
                        f"Preprocessing worker (role={role}) was restarted; "
                        f"task {task.id} was interrupted before completion."
                    ),
                    prefix="Preprocessing was interrupted before it completed. Please retry.",
                )
                for ft in task.file_tasks:
                    if ft.status in (
                        models.PreprocessingStatus.PENDING,
                        models.PreprocessingStatus.IN_PROGRESS,
                    ):
                        ft.status = models.PreprocessingStatus.FAILED
                        ft.error_message = msg
                        ft.completed_at = now

                completed = sum(
                    1
                    for ft in task.file_tasks
                    if ft.status == models.PreprocessingStatus.COMPLETED
                )
                failed = sum(
                    1
                    for ft in task.file_tasks
                    if ft.status == models.PreprocessingStatus.FAILED
                )
                cancelled = sum(
                    1
                    for ft in task.file_tasks
                    if ft.status == models.PreprocessingStatus.CANCELLED
                )
                task.processed_files = completed + failed + cancelled
                task.failed_files = failed
                task.skipped_files = cancelled
                task.status = models.PreprocessingStatus.FAILED
                task.message = msg
                task.completed_at = now
                finalized_ids.append(task.id)
                reclaimed += 1
            db.commit()

            for tid in finalized_ids:
                task = db.get(models.PreprocessingTask, tid)
                if task:
                    _broadcast_preprocessing_update(task, "failed")

        elif role == "default":
            trials = (
                db.query(models.Trial)
                .filter(models.Trial.status == models.TrialStatus.PROCESSING)
                .all()
            )
            for trial in trials:
                trial.status = models.TrialStatus.FAILED
                trial.finished_at = now
                msg = operational_error_message(
                    detail=(
                        f"Worker (role={role}) was restarted; trial {trial.id} "
                        "was interrupted before completion."
                    ),
                    prefix="The trial was interrupted before it completed. Please retry.",
                )
                trial.meta = (trial.meta or {}) | {
                    "failures": {"_restart": msg},
                    "eta_seconds": 0,
                }
                reclaimed += 1
            db.commit()

            for trial in trials:
                _broadcast_trial_update(trial, "failed")

    return f"reclaimed {reclaimed} orphaned {role} task(s) on startup"


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
        """Register the periodic orphan sweeper (ORPHAN_SWEEP_INTERVAL_SECONDS)."""
        sender.add_periodic_task(
            settings.ORPHAN_SWEEP_INTERVAL_SECONDS,
            sweep_orphans_task.s(),
            name="sweep_orphaned_file_tasks",
        )

    @signals.worker_ready.connect
    def _reclaim_on_worker_ready(sender=None, **_):
        """React to a restart the instant this worker is up.

        Runs once in the worker's main process when it's ready to consume:
          1. Kick the staleness sweeper immediately so a restart triggers
             reconciliation now instead of waiting for the next beat interval.
          2. Aggressively finalize work this worker's queue abandoned on the
             previous run (see ``reclaim_orphaned_on_startup``). Gated by
             CELERY_WORKER_ROLE so it only touches the queue this worker owns;
             unset → skipped (multi-worker-safe; sweeper still covers it).
        """
        import os

        try:
            logger.info("Worker ready: %s", sweep_orphans())
        except Exception as e:  # pragma: no cover - best effort
            logger.warning("Startup sweep failed: %s", e, exc_info=True)

        role = os.environ.get("CELERY_WORKER_ROLE")
        if role in ("preprocess", "default"):
            try:
                logger.info("Worker ready: %s", reclaim_orphaned_on_startup(role))
            except Exception as e:  # pragma: no cover - best effort
                logger.warning("Startup reclaim failed: %s", e, exc_info=True)

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
    def _dispose_engine_on_fork(**_):
        """Reset the SQLAlchemy connection pool in each forked worker process.

        The engine (and its pooled connections) is created at import time in the
        parent process. Celery forks worker child processes which inherit those
        live Postgres socket FDs. If two processes ever use the same inherited
        connection concurrently — e.g. the settings-invalidation listener thread
        in every worker waking at once on an admin settings change — the wire
        protocol corrupts, surfacing as "server closed the connection
        unexpectedly" / "there is already a transaction in progress".

        ``dispose(close=False)`` drops the inherited connections from this
        child's pool WITHOUT closing the underlying sockets (which still belong
        to the parent), so each worker lazily opens its own fresh connections.
        """
        try:
            from ..db.session import engine

            engine.dispose(close=False)
        except Exception as e:  # pragma: no cover - best effort
            logger.warning("Failed to dispose engine pool on worker init: %s", e)

    @signals.worker_process_init.connect
    def _start_settings_listener(**_):
        """Start the settings-invalidation subscriber per worker process."""
        _settings_invalidation_listener()
