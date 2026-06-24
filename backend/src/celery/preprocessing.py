# backend/src/celery/preprocessing.py
import asyncio
import datetime as dt
import logging

from sqlalchemy import func, select

from .. import models
from ..core.config import settings
from ..dependencies import get_db
from ..utils.preprocessing import PreprocessingPipeline
from .celery_config import celery_app

log = logging.getLogger(__name__)


def _count_file_tasks_by_status(
    db, task_id: int
) -> dict[models.PreprocessingStatus, int]:
    """Count a task's FilePreprocessingTasks grouped by status in one query.

    Replaces iterating the full ``task.file_tasks`` collection (4+ passes) on
    every heartbeat tick — O(rows) Python work every 3s → a single GROUP BY.
    """
    rows = db.execute(
        select(models.FilePreprocessingTask.status, func.count())
        .where(models.FilePreprocessingTask.preprocessing_task_id == task_id)
        .group_by(models.FilePreprocessingTask.status)
    ).all()
    return {status: count for status, count in rows}


def _broadcast_preprocessing_update(
    task: models.PreprocessingTask, event: str = "progress"
):
    """Broadcast preprocessing task update via Redis pub/sub (for use in Celery tasks).

    Since Celery workers run in separate processes/containers from FastAPI,
    we use Redis pub/sub to send messages to the FastAPI backend, which then
    broadcasts to connected WebSocket clients.

    Includes full task data so frontend can display complete task information.
    """
    try:
        from ..utils.redis_broadcast import publish_task_update

        # Build full task data for frontend display
        task_data = {
            "type": "preprocessing_update",
            "task_id": task.id,
            "project_id": task.project_id,
            "status": task.status.value
            if hasattr(task.status, "value")
            else str(task.status),
            "processed_files": task.processed_files,
            "total_files": task.meta.get("total_files", 0)
            if task.meta
            else task.total_files,
            "failed_files": task.failed_files,
            "cancelled_files": task.skipped_files,
            "configuration_name": task.configuration.name
            if task.configuration
            else None,
            "configuration": {
                "id": task.configuration.id,
                "name": task.configuration.name,
                "additional_settings": task.configuration.additional_settings,
            }
            if task.configuration
            else None,
            "meta": task.meta,
            "event": event,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }

        publish_task_update(task_data)
    except ImportError as e:
        log.debug("Redis broadcast not available: %s", e)
    except Exception as e:
        log.error("Error broadcasting preprocessing update: %s", e, exc_info=True)


if celery_app:

    @celery_app.task(
        bind=True,
        # Note: We don't use autoretry_for because exceptions during processing
        # are handled manually (file_task marked as FAILED). Auto-retry would
        # cause "INTRANS" errors since the DB session is left in a bad state.
        # Worker-lost detection is handled via started_at check in the task body.
        queue="preprocess",
        # Ensure task acknowledgment happens AFTER the transaction completes
        # to avoid leaving connections in INTRANS state on worker crash
        acks_late=True,
        reject_on_worker_lost=True,
    )
    def process_files_async(
        self,
        task_id: int,
    ):
        async def _run():
            failures = {}

            # --- Setup: fetch the task + mark IN_PROGRESS ---
            # Use get_fresh_db() to ensure we get a clean connection
            # even on retry (avoids "INTRANS" state from previous attempt)
            with next(get_db()) as db:
                task: models.PreprocessingTask = db.get(
                    models.PreprocessingTask, task_id
                )
                if not task:
                    raise ValueError(f"PreprocessingTask with id {task_id} not found")

                # Read custom OCR credentials from the task row. The api_key is
                # stored encrypted (api_key_encrypted) and decrypted here; it is
                # never passed through the Celery broker as plaintext. base_url
                # is not secret and lives in task_metadata.
                api_key = task.api_key or None
                base_url = (task.task_metadata or {}).get("api_base_url")

                # ── Re-delivery after worker lost / stale job detection ──
                # When a worker is killed by SIGKILL (OOM etc.) Celery
                # rejects the message and the broker re-queues it.  On the
                # next delivery `started_at` will already be set (from the
                # first run's commit on line 90 below) and `status` will be
                # IN_PROGRESS because the worker died before reaching the
                # finalization block.  We detect this and fail immediately
                # instead of looping forever.
                # This also handles any edge cases where tasks get stuck
                # in IN_PROGRESS due to unhandled exceptions or crashes.
                now = dt.datetime.now(dt.UTC)
                if task.started_at is not None and task.status in (
                    models.PreprocessingStatus.PENDING,
                    models.PreprocessingStatus.IN_PROGRESS,
                ):
                    # Check how long ago the task started
                    time_since_start = (now - task.started_at).total_seconds()
                    task.status = models.PreprocessingStatus.FAILED
                    task.completed_at = now
                    if time_since_start > 300:  # More than 5 minutes
                        task.message = (
                            f"Preprocessing failed: worker crashed after {time_since_start:.0f}s "
                            "(out-of-memory, process crash, or unhandled exception). "
                            "This file may be too large. Check worker logs for details."
                        )
                    else:
                        task.message = (
                            "Preprocessing failed: detected stale/incomplete task "
                            "(worker crash or unhandled exception). "
                            "Check worker logs for details."
                        )
                    # Mark any pending/in-progress file tasks as failed
                    for ft in task.file_tasks:
                        if ft.status in (
                            models.PreprocessingStatus.PENDING,
                            models.PreprocessingStatus.IN_PROGRESS,
                        ):
                            ft.status = models.PreprocessingStatus.FAILED
                            ft.error_message = task.message
                            ft.completed_at = now
                    db.commit()

                    # Broadcast the failure via WebSocket so UI updates in real-time
                    _broadcast_preprocessing_update(task, "failed")

                    log.warning(
                        "PreprocessingTask %s: detected stale task (started_at=%s, %ds ago). "
                        "Marking as FAILED.",
                        task_id,
                        task.started_at,
                        time_since_start,
                    )
                    return

                # Mark the task as in_progress immediately so the frontend
                # never sees a stale PENDING status after Celery accepted it.
                task.status = models.PreprocessingStatus.IN_PROGRESS
                task.started_at = now
                db.commit()

                file_tasks = [
                    ft
                    for ft in task.file_tasks
                    if ft.status == models.PreprocessingStatus.PENDING
                ]

                # Get configuration to determine appropriate concurrency
                additional_settings = (
                    task.configuration.additional_settings if task.configuration else {}
                )
                ocr_engine = additional_settings.get("ocr_engine", "docling_tesseract")
                extraction_mode = additional_settings.get("extraction_mode", "auto")

                # Determine concurrency limit based on OCR backend
                # This ensures we don't overwhelm specific backends
                if (
                    ocr_engine == "mistral_ocr"
                    or extraction_mode == "high_accuracy_remote"
                ):
                    max_concurrent = settings.MISTRAL_OCR_MAX_CONCURRENT_FILES
                elif ocr_engine == "llm_vision":
                    max_concurrent = settings.VISION_OCR_MAX_CONCURRENT_FILES
                else:
                    # Default to docling-serve or general limit
                    max_concurrent = min(
                        settings.DOCLING_SERVE_MAX_CONCURRENT_FILES,
                        settings.PREPROCESS_MAX_CONCURRENT_FILES,
                    )

                log.info(
                    "Starting preprocessing task %s with concurrency limit %d (OCR engine: %s)",
                    task_id,
                    max_concurrent,
                    ocr_engine,
                )

            sem = asyncio.Semaphore(max_concurrent)
            running_tasks = {}

            # --- Process one file_task coroutine ---
            async def process_file(file_task_id: int):
                try:
                    async with sem:
                        with next(get_db()) as db:
                            task = db.get(models.PreprocessingTask, task_id)
                            if task.is_cancelled:
                                raise asyncio.CancelledError(
                                    "Preprocessing cancelled before file start"
                                )

                            file_task = db.get(
                                models.FilePreprocessingTask, file_task_id
                            )
                            if file_task.status != models.PreprocessingStatus.PENDING:
                                return

                        def blocking_run():
                            log.debug(
                                "blocking_run: starting for file_task_id=%s",
                                file_task_id,
                            )
                            with next(get_db()) as db:
                                try:
                                    _ = db.get(models.PreprocessingTask, task_id)
                                    file_task = db.get(
                                        models.FilePreprocessingTask, file_task_id
                                    )
                                    log.debug(
                                        "blocking_run: got file_task, creating pipeline"
                                    )
                                    pipeline = PreprocessingPipeline(
                                        db,
                                        task_id,
                                        api_key=api_key,
                                        base_url=base_url,
                                    )
                                    if pipeline.check_cancelled():
                                        raise asyncio.CancelledError(
                                            "Cancelled before processing file"
                                        )
                                    log.debug(
                                        "blocking_run: calling _process_file_task"
                                    )
                                    pipeline._process_file_task(file_task)
                                    log.debug(
                                        "blocking_run: _process_file_task completed"
                                    )
                                except Exception as e:
                                    # Explicit rollback before re-raising
                                    # This ensures the connection is clean for Celery retry
                                    log.error(
                                        "blocking_run: exception: %s", e, exc_info=True
                                    )
                                    db.rollback()
                                    raise
                                finally:
                                    # A fresh pipeline is built per file task in
                                    # the async path; close its OpenAI/docling-serve
                                    # clients so their httpx pools don't leak across
                                    # the (potentially long-lived) Celery worker.
                                    # ``pipeline`` may be unbound if the constructor
                                    # itself raised, so guard before closing.
                                    try:
                                        pipeline.close()
                                    except UnboundLocalError:
                                        pass
                                    except Exception:
                                        log.debug(
                                            "blocking_run: error closing pipeline",
                                            exc_info=True,
                                        )

                        await asyncio.to_thread(blocking_run)

                except asyncio.CancelledError:
                    with next(get_db()) as db:
                        file_task = db.get(models.FilePreprocessingTask, file_task_id)
                        file_task.status = models.PreprocessingStatus.CANCELLED
                        file_task.completed_at = dt.datetime.now(dt.UTC)
                        db.commit()
                    raise
                except Exception as exc:
                    failures[str(file_task_id)] = str(exc)
                    # Use a fresh session for the status update to avoid any
                    # transaction state issues from the failed operation
                    with next(get_db()) as db:
                        file_task = db.get(models.FilePreprocessingTask, file_task_id)
                        file_task.status = models.PreprocessingStatus.FAILED
                        file_task.error_message = str(exc)
                        file_task.completed_at = dt.datetime.now(dt.UTC)
                        db.commit()

            # --- Launch all file_tasks (concurrent up to limit) ---
            for ft in file_tasks:
                running_tasks[ft.id] = asyncio.create_task(process_file(ft.id))

            # --- Heartbeat: update progress/meta/ETA for frontend + WebSocket broadcast ---
            async def progress_heartbeat():
                last_broadcast = None
                try:
                    while True:
                        await asyncio.sleep(3)
                        with next(get_db()) as db:
                            task = db.get(models.PreprocessingTask, task_id)
                            if not task:
                                break

                            # Count file tasks by status in one GROUP BY query
                            # instead of iterating task.file_tasks 4+ times.
                            counts = _count_file_tasks_by_status(db, task_id)
                            completed = counts.get(
                                models.PreprocessingStatus.COMPLETED, 0
                            )
                            failed = counts.get(models.PreprocessingStatus.FAILED, 0)
                            cancelled = counts.get(
                                models.PreprocessingStatus.CANCELLED, 0
                            )
                            in_progress = counts.get(
                                models.PreprocessingStatus.IN_PROGRESS, 0
                            )
                            total = sum(counts.values())

                            now = dt.datetime.now(dt.UTC)
                            started = task.started_at or now
                            elapsed = (
                                (now - started).total_seconds() if completed else 0
                            )
                            remaining = total - completed - failed - cancelled
                            eta = (
                                int(elapsed / completed * remaining)
                                if completed > 0 and remaining > 0
                                else 0
                            )

                            task.processed_files = completed + failed + cancelled
                            task.failed_files = failed
                            task.skipped_files = cancelled
                            task.meta = (task.meta or {}) | {
                                "eta_seconds": eta,
                                "in_progress": in_progress,
                                "total_files": total,
                                "completed_files": completed,
                                "failed_files": failed,
                                "cancelled_files": cancelled,
                            }
                            db.commit()

                            # Broadcast update via Redis pub/sub (FastAPI will relay to WebSocket clients)
                            current_state = (task.status, completed, failed, cancelled)
                            if last_broadcast != current_state:
                                last_broadcast = current_state
                                _broadcast_preprocessing_update(task, "progress")

                            # Done once no file task is still pending/in-progress.
                            if not in_progress and not counts.get(
                                models.PreprocessingStatus.PENDING, 0
                            ):
                                break
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    log.error(
                        "Heartbeat error for task %s: %s", task_id, e, exc_info=True
                    )
                    raise

            # --- Cancellation watcher: cancels all running file tasks ---
            async def cancellation_watcher():
                while True:
                    await asyncio.sleep(1)
                    with next(get_db()) as db:
                        task = db.get(models.PreprocessingTask, task_id)
                        if task.is_cancelled:
                            for t in running_tasks.values():
                                if not t.done():
                                    t.cancel()
                            break
                    if all(t.done() for t in running_tasks.values()):
                        break

            await asyncio.gather(
                asyncio.gather(*running_tasks.values(), return_exceptions=True),
                progress_heartbeat(),
                cancellation_watcher(),
            )

            # --- Finalization: update all remaining statuses, handle doc rollback ---
            with next(get_db()) as db:
                task = db.get(models.PreprocessingTask, task_id)
                now = dt.datetime.now(dt.UTC)

                # Mark any not-done file_tasks as CANCELLED
                for ft in task.file_tasks:
                    if ft.status in [
                        models.PreprocessingStatus.PENDING,
                        models.PreprocessingStatus.IN_PROGRESS,
                    ]:
                        ft.status = models.PreprocessingStatus.CANCELLED
                        ft.completed_at = now

                db.commit()

                # Count by status in one GROUP BY query instead of 3 passes
                # over task.file_tasks. total = actual file-task row count
                # (matches the previous len(task.file_tasks)).
                counts = _count_file_tasks_by_status(db, task_id)
                total = sum(counts.values())
                completed = counts.get(models.PreprocessingStatus.COMPLETED, 0)
                failed = counts.get(models.PreprocessingStatus.FAILED, 0)
                cancelled = counts.get(models.PreprocessingStatus.CANCELLED, 0)

                task.completed_at = now

                if task.is_cancelled:
                    task.status = models.PreprocessingStatus.CANCELLED
                    event = "cancelled"
                    # Handle keep/delete processed docs on cancel
                    if task.rollback_on_cancel:
                        deleted_count = 0
                        for file_task in task.file_tasks:
                            # Include CANCELLED file_tasks: a row-by-row CSV
                            # file_task commits documents in batches (every
                            # BATCH_SIZE rows), so one cancelled mid-flight
                            # can have many committed documents in the DB.
                            # Skipping them here would leave orphaned docs
                            # that pollute the project and can be picked up
                            # by trials despite the "rolled back" message.
                            if file_task.status in (
                                models.PreprocessingStatus.COMPLETED,
                                models.PreprocessingStatus.CANCELLED,
                            ):
                                for doc in file_task.documents:
                                    doc.document_sets.clear()
                                    db.delete(doc)
                                    deleted_count += 1
                        task.message = f"Task cancelled and {deleted_count} processed documents rolled back"
                    else:
                        task.message = "Task cancelled, keeping processed documents"
                elif completed == total and total > 0:
                    task.status = models.PreprocessingStatus.COMPLETED
                    event = "completed"
                    task.message = "All files processed successfully."
                elif failed == total:
                    task.status = models.PreprocessingStatus.FAILED
                    event = "failed"
                    task.message = "All files failed to preprocess."
                else:
                    task.status = models.PreprocessingStatus.FAILED
                    event = "failed"
                    task.message = (
                        f"{completed} of {total} files processed successfully, "
                        f"{failed} failed, {cancelled} cancelled."
                    )
                db.commit()

                # Broadcast final status via Redis pub/sub (FastAPI will relay to WebSocket clients)
                _broadcast_preprocessing_update(task, event)

        asyncio.run(_run())

    # NOTE: a previous task_failure handler lived here to mark the
    # PreprocessingTask FAILED after retries were exhausted, but Celery's
    # task_failure signal sends ``args`` (not ``body``), so its ``body``
    # guard caused it to return immediately and never run. The global
    # ``mark_failed`` handler in celery/task_signals.py already covers this
    # case correctly (it reads ``args[0]``), so the dead handler was removed.
