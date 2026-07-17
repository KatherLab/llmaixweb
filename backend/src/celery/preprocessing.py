# backend/src/celery/preprocessing.py
import asyncio
import datetime as dt
import logging
import threading

from sqlalchemy import func, select

from .. import models
from ..core.config import settings
from ..dependencies import get_db
from ..middleware.error_handlers import (
    internal_error_message,
    operational_error_message,
)
from ..schemas.project import redact_ocr_secrets
from ..utils.preprocessing import PreprocessingPipeline
from .celery_config import celery_app

log = logging.getLogger(__name__)

# Fraction of the Celery soft time limit a single preprocessing chunk is allowed
# to consume in the worst case (every file running to its full per-file timeout).
# The margin below 1.0 leaves room for setup, the final commit, and the
# re-enqueue so a chunk never actually trips SoftTimeLimitExceeded.
_CHUNK_TIME_BUDGET_FRACTION = 0.75

# On cancel-with-rollback, how long to wait for abandoned worker threads to
# drain before deleting produced documents. asyncio's t.cancel() aborts the
# coroutine awaiting to_thread() but the OS thread keeps running until it hits a
# cooperative check_cancelled() point; deleting docs before it exits would let a
# late commit survive as an orphan. Row-by-row threads drain within ~100 rows;
# this window comfortably covers that.
_CANCEL_THREAD_DRAIN_SECONDS = 30


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
                # Redact OCR credentials so keys never leave the server via the
                # WebSocket broadcast (mirrors the API-response serializer).
                "additional_settings": redact_ocr_secrets(
                    task.configuration.additional_settings
                ),
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
        resumed: bool = False,
    ):
        # ``resumed=True`` marks a self-continuation: this task processes files in
        # chunks (PREPROCESS_CHUNK_SIZE per execution) and re-enqueues itself to
        # finish the rest, so a huge batch never runs under a single time limit /
        # broker visibility window. A resume is an intentional re-dispatch, not a
        # worker-crash redelivery, so the stale-task guard below is skipped for it.
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

                # ── Re-delivery guard: terminal tasks ──
                # With task_acks_late=True and a Redis visibility_timeout, a
                # message can be redelivered after a worker loss or a task that
                # exceeded the visibility window — by which point this task may
                # already have been finalized as COMPLETED/FAILED/CANCELLED
                # (by the original run or the sweeper in task_signals.py).
                # Re-running would resurrect a terminal task (status flaps
                # COMPLETED -> IN_PROGRESS -> ...) and waste OCR cost on
                # duplicate work. Bail out. Mirrors the trial task
                # (celery/info_extraction.py).
                if task.status in (
                    models.PreprocessingStatus.COMPLETED,
                    models.PreprocessingStatus.FAILED,
                    models.PreprocessingStatus.CANCELLED,
                ):
                    log.warning(
                        "PreprocessingTask %s: already terminal (%s), "
                        "skipping re-delivery",
                        task_id,
                        task.status,
                    )
                    return

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
                if (
                    not resumed
                    and task.started_at is not None
                    and task.status
                    in (
                        models.PreprocessingStatus.PENDING,
                        models.PreprocessingStatus.IN_PROGRESS,
                    )
                ):
                    # Check how long ago the task started
                    time_since_start = (now - task.started_at).total_seconds()
                    task.status = models.PreprocessingStatus.FAILED
                    task.completed_at = now
                    # Record the crash/stale-detection detail (timing + likely
                    # cause) in the error log under an id; show only a generic
                    # message + that id so no infra detail reaches the user.
                    task.message = operational_error_message(
                        detail=(
                            f"PreprocessingTask {task_id} detected stale after "
                            f"{time_since_start:.0f}s (worker crash / OOM / unhandled "
                            "exception on re-delivery); marking FAILED."
                        ),
                        prefix="Preprocessing failed before it could complete. Please retry.",
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
                # Preserve the original started_at across resumes (accurate ETA).
                task.status = models.PreprocessingStatus.IN_PROGRESS
                if task.started_at is None:
                    task.started_at = now
                db.commit()

                # Get configuration to determine appropriate concurrency
                additional_settings = (
                    task.configuration.additional_settings if task.configuration else {}
                )
                ocr_engine = additional_settings.get("ocr_engine", "docling_tesseract")
                extraction_mode = additional_settings.get("extraction_mode", "auto")

                # Determine concurrency limit + worst-case per-file timeout based
                # on the OCR backend. This ensures we don't overwhelm specific
                # backends, and lets us bound the chunk by time (below).
                if (
                    ocr_engine == "mistral_ocr"
                    or extraction_mode == "high_accuracy_remote"
                ):
                    max_concurrent = settings.MISTRAL_OCR_MAX_CONCURRENT_FILES
                    engine_file_timeout = settings.MISTRAL_OCR_FILE_TIMEOUT_SECONDS
                elif ocr_engine == "llm_vision":
                    max_concurrent = settings.VISION_OCR_MAX_CONCURRENT_FILES
                    engine_file_timeout = settings.VISION_OCR_FILE_TIMEOUT_SECONDS
                else:
                    # Default to docling-serve or general limit
                    max_concurrent = min(
                        settings.DOCLING_SERVE_MAX_CONCURRENT_FILES,
                        settings.PREPROCESS_MAX_CONCURRENT_FILES,
                    )
                    engine_file_timeout = settings.DOCLING_SERVE_FILE_TIMEOUT_SECONDS
                # A chunk may contain mixed file types; a table/text file falls
                # back to the general timeout, so take the max as the worst case.
                per_file_timeout = max(
                    engine_file_timeout, settings.PREPROCESS_FILE_TIMEOUT_SECONDS
                )

                # Bound the chunk by TIME as well as count. Even at the configured
                # PREPROCESS_CHUNK_SIZE, a chunk of slow files can blow the task's
                # soft time limit — e.g. 200 files at docling's 900s timeout /
                # concurrency 3 needs ~16h, far past the 6h limit — and when
                # SoftTimeLimitExceeded fires it kills the whole *remaining* batch
                # (mark_failed), defeating the point of chunking. Worst-case wall
                # time for C files at concurrency N is ceil(C / N) * T, i.e. it
                # advances in whole *waves* of N files — so size the chunk as
                # full waves (C = floor(budget / T) * N) rather than C ≤
                # N * budget / T, whose ceil(C / N) can overshoot the budget by
                # almost a full T. At least one wave always runs (progress
                # guarantee), even when a single T exceeds the budget. Typical
                # files finish well under T, so a fast chunk simply re-enqueues
                # sooner (which also improves fairness).
                time_budget = int(
                    settings.CELERY_TASK_SOFT_TIME_LIMIT_SECONDS
                    * _CHUNK_TIME_BUDGET_FRACTION
                )
                waves = max(1, time_budget // max(1, per_file_timeout))
                max_by_time = waves * max_concurrent
                chunk_size = min(settings.PREPROCESS_CHUNK_SIZE, max_by_time)

                # Process at most chunk_size PENDING files this execution; the
                # finalization block re-enqueues the task to continue the rest.
                file_tasks = [
                    ft
                    for ft in task.file_tasks
                    if ft.status == models.PreprocessingStatus.PENDING
                ][:chunk_size]

                log.info(
                    "Starting preprocessing task %s with concurrency limit %d, "
                    "chunk size %d (OCR engine: %s, per-file timeout %ds)",
                    task_id,
                    max_concurrent,
                    chunk_size,
                    ocr_engine,
                    per_file_timeout,
                )

            sem = asyncio.Semaphore(max_concurrent)
            running_tasks = {}
            # Tracks OS worker threads currently inside blocking_run. The
            # finalization waits for this to reach 0 before a cancel rollback so
            # an abandoned (t.cancel()'d) thread can't commit documents after we
            # delete them. Touched from worker threads → guarded by a lock.
            thread_tracker = {"active": 0}
            thread_lock = threading.Lock()

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
                            with thread_lock:
                                thread_tracker["active"] += 1
                            try:
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
                                            "blocking_run: exception: %s",
                                            e,
                                            exc_info=True,
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
                            finally:
                                # Decrement only after the thread has fully
                                # finished (incl. any final commit), so the
                                # finalization drain-wait can trust "active == 0".
                                with thread_lock:
                                    thread_tracker["active"] -= 1

                        await asyncio.to_thread(blocking_run)

                except asyncio.CancelledError:
                    with next(get_db()) as db:
                        file_task = db.get(models.FilePreprocessingTask, file_task_id)
                        file_task.status = models.PreprocessingStatus.CANCELLED
                        file_task.completed_at = dt.datetime.now(dt.UTC)
                        db.commit()
                    raise
                except Exception as exc:
                    safe_msg = internal_error_message(
                        exc, prefix="File processing failed"
                    )
                    failures[str(file_task_id)] = safe_msg
                    # Use a fresh session for the status update to avoid any
                    # transaction state issues from the failed operation
                    with next(get_db()) as db:
                        file_task = db.get(models.FilePreprocessingTask, file_task_id)
                        file_task.status = models.PreprocessingStatus.FAILED
                        file_task.error_message = safe_msg
                        file_task.completed_at = dt.datetime.now(dt.UTC)
                        db.commit()

            # --- Launch all file_tasks (concurrent up to limit) ---
            for ft in file_tasks:
                running_tasks[ft.id] = asyncio.create_task(process_file(ft.id))

            # --- Heartbeat: update progress/meta/ETA for frontend + WebSocket broadcast ---
            async def progress_heartbeat():
                last_broadcast = None
                while True:
                    await asyncio.sleep(3)
                    # A transient failure in one tick (DB pool exhaustion, a
                    # restart blip) must NOT fail the whole batch — the actual
                    # work lives in running_tasks. Catch per-tick, log, and retry
                    # next tick. The done-check below is outside the try so a
                    # heartbeat hiccup can never strand the loop.
                    try:
                        with next(get_db()) as db:
                            task = db.get(models.PreprocessingTask, task_id)
                            if task is not None:
                                # Count file tasks by status in one GROUP BY query
                                # instead of iterating task.file_tasks 4+ times.
                                counts = _count_file_tasks_by_status(db, task_id)
                                completed = counts.get(
                                    models.PreprocessingStatus.COMPLETED, 0
                                )
                                failed = counts.get(
                                    models.PreprocessingStatus.FAILED, 0
                                )
                                cancelled = counts.get(
                                    models.PreprocessingStatus.CANCELLED, 0
                                )
                                in_progress = counts.get(
                                    models.PreprocessingStatus.IN_PROGRESS, 0
                                )
                                total = sum(counts.values())

                                now = dt.datetime.now(dt.UTC)
                                started = task.started_at or now
                                # Coerce to tz-aware: Postgres returns aware
                                # datetimes but SQLite (dev) returns naive, which
                                # can't be subtracted from the aware `now`.
                                if started.tzinfo is None:
                                    started = started.replace(tzinfo=dt.UTC)
                                elapsed = (
                                    (now - started).total_seconds() if completed else 0
                                )
                                remaining = total - completed - failed - cancelled
                                eta = (
                                    int(elapsed / completed * remaining)
                                    if completed > 0 and remaining > 0
                                    else 0
                                )

                                # processed_files counts successful completions
                                # ONLY — app-wide convention shared by the
                                # pipeline tally, the orphan sweeper, and the
                                # progress endpoint's remaining-files math
                                # (total - processed - failed). Failed/cancelled
                                # are carried separately below.
                                task.processed_files = completed
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

                                # Broadcast via Redis pub/sub (FastAPI relays it
                                # to WebSocket clients) only on state change.
                                current_state = (
                                    task.status,
                                    completed,
                                    failed,
                                    cancelled,
                                )
                                if last_broadcast != current_state:
                                    last_broadcast = current_state
                                    _broadcast_preprocessing_update(task, "progress")
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        log.error(
                            "Heartbeat error for task %s (continuing): %s",
                            task_id,
                            e,
                            exc_info=True,
                        )

                    # Done once THIS chunk's file tasks have all finished. (There
                    # may be further PENDING files belonging to later chunks that
                    # a subsequent resume handles — so we key off this execution's
                    # running_tasks, not the global PENDING count.)
                    if all(t.done() for t in running_tasks.values()):
                        break

            # --- Cancellation watcher: cancels all running file tasks ---
            async def cancellation_watcher():
                while True:
                    await asyncio.sleep(1)
                    # Resilient per-tick: a transient DB error must not stop the
                    # watcher, or a cancel request would never abort in-flight
                    # files. Log and retry next tick.
                    try:
                        with next(get_db()) as db:
                            task = db.get(models.PreprocessingTask, task_id)
                            if task is not None and task.is_cancelled:
                                for t in running_tasks.values():
                                    if not t.done():
                                        t.cancel()
                                break
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        log.error(
                            "Cancellation watcher error for task %s (continuing): %s",
                            task_id,
                            e,
                            exc_info=True,
                        )
                    if all(t.done() for t in running_tasks.values()):
                        break

            # return_exceptions=True on the OUTER gather too: an unexpected raise
            # in the heartbeat/watcher must not cancel the sibling file-processing
            # coroutines (gather cancels siblings on the first exception when
            # return_exceptions=False). Finalization reads authoritative DB state
            # regardless of these auxiliary coroutines' return values.
            await asyncio.gather(
                asyncio.gather(*running_tasks.values(), return_exceptions=True),
                progress_heartbeat(),
                cancellation_watcher(),
                return_exceptions=True,
            )

            # --- Zombie-thread drain before a cancel rollback ---
            # asyncio.gather returns as soon as the coroutines settle, but a
            # t.cancel()'d coroutine abandons the OS thread still running inside
            # blocking_run; that thread keeps going until it reaches a
            # cooperative check_cancelled() point and may commit more documents.
            # If we rolled those back now, the late commit would survive as an
            # orphan. So when this task is being cancelled WITH rollback, wait
            # (bounded) for in-flight threads to exit first, making the rollback
            # below authoritative. Only relevant on cancel; the normal completion
            # path has no abandoned threads.
            with next(get_db()) as db:
                _t = db.get(models.PreprocessingTask, task_id)
                _drain_needed = bool(_t and _t.is_cancelled and _t.rollback_on_cancel)
            if _drain_needed:
                for _ in range(int(_CANCEL_THREAD_DRAIN_SECONDS / 0.1)):
                    with thread_lock:
                        if thread_tracker["active"] == 0:
                            break
                    await asyncio.sleep(0.1)
                else:
                    with thread_lock:
                        _still_active = thread_tracker["active"]
                    log.warning(
                        "PreprocessingTask %s: %d worker thread(s) still active "
                        "after %ds drain window; proceeding with cancel rollback "
                        "(a slow in-flight file may leave up to one orphan doc)",
                        task_id,
                        _still_active,
                        _CANCEL_THREAD_DRAIN_SECONDS,
                    )

            # --- Chunk boundary: continue with the next chunk, or finalize ---
            with next(get_db()) as db:
                task = db.get(models.PreprocessingTask, task_id)
                now = dt.datetime.now(dt.UTC)

                # If the task wasn't cancelled and PENDING files remain beyond
                # this chunk, re-enqueue to continue instead of finalizing. The
                # re-enqueued message goes to the back of the queue, so other
                # users' batches interleave fairly at chunk granularity.
                pending_remaining = (
                    db.scalar(
                        select(func.count())
                        .select_from(models.FilePreprocessingTask)
                        .where(
                            models.FilePreprocessingTask.preprocessing_task_id
                            == task_id,
                            models.FilePreprocessingTask.status
                            == models.PreprocessingStatus.PENDING,
                        )
                    )
                    or 0
                )

                if not task.is_cancelled and pending_remaining > 0:
                    counts = _count_file_tasks_by_status(db, task_id)
                    completed = counts.get(models.PreprocessingStatus.COMPLETED, 0)
                    failed = counts.get(models.PreprocessingStatus.FAILED, 0)
                    cancelled = counts.get(models.PreprocessingStatus.CANCELLED, 0)
                    # Same convention as the heartbeat above: completed only.
                    task.processed_files = completed
                    task.failed_files = failed
                    task.skipped_files = cancelled
                    task.status = models.PreprocessingStatus.IN_PROGRESS
                    task.meta = (task.meta or {}) | {
                        "total_files": sum(counts.values()),
                        "completed_files": completed,
                    }
                    db.commit()
                    _broadcast_preprocessing_update(task, "progress")
                    log.info(
                        "PreprocessingTask %s: chunk done, %d files remaining — "
                        "will re-enqueue to continue",
                        task_id,
                        pending_remaining,
                    )
                    # Signal the (sync) task body to re-enqueue AFTER the event
                    # loop unwinds — re-enqueuing here (inside asyncio.run) would
                    # nest asyncio.run under Celery's eager mode.
                    return True

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
                        # Include CANCELLED and FAILED file_tasks too: a
                        # row-by-row CSV file_task commits documents in
                        # batches (every BATCH_SIZE rows), so one that was
                        # cancelled or FAILED mid-flight can still have many
                        # committed documents in the DB. Skipping them would
                        # leave orphaned docs that pollute the project and can
                        # be picked up by trials despite the "rolled back"
                        # message.
                        candidate_docs = [
                            doc
                            for file_task in task.file_tasks
                            if file_task.status
                            in (
                                models.PreprocessingStatus.COMPLETED,
                                models.PreprocessingStatus.CANCELLED,
                                models.PreprocessingStatus.FAILED,
                            )
                            for doc in file_task.documents
                        ]
                        # Keep docs a trial result / evaluation metric points at:
                        # those FKs are ON DELETE RESTRICT, so deleting them
                        # would fail the whole finalization commit. Mirrors the
                        # cancel endpoint's guard.
                        blocked: set[int] = set()
                        candidate_ids = [doc.id for doc in candidate_docs]
                        if candidate_ids:
                            blocked = set(
                                db.execute(
                                    select(models.TrialResult.document_id).where(
                                        models.TrialResult.document_id.in_(
                                            candidate_ids
                                        )
                                    )
                                ).scalars()
                            )
                            blocked |= set(
                                db.execute(
                                    select(models.EvaluationMetric.document_id).where(
                                        models.EvaluationMetric.document_id.in_(
                                            candidate_ids
                                        )
                                    )
                                ).scalars()
                            )
                        for doc in candidate_docs:
                            if doc.id in blocked:
                                continue
                            doc.document_sets.clear()
                            db.delete(doc)
                            deleted_count += 1
                        task.message = f"Task cancelled and {deleted_count} processed documents rolled back"
                        if blocked:
                            task.message += (
                                f"; {len(blocked)} document(s) kept because trial "
                                "results or evaluations still reference them"
                            )
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
                # Sync the persisted counters with the final tally — the last
                # heartbeat tick may predate the just-cancelled file tasks
                # above (and heartbeats stop once this finalization starts).
                task.processed_files = completed
                task.failed_files = failed
                task.skipped_files = cancelled
                db.commit()

                # Broadcast final status via Redis pub/sub (FastAPI will relay to WebSocket clients)
                _broadcast_preprocessing_update(task, event)

        # _run() returns True when this chunk finished but PENDING files remain,
        # meaning the task should re-enqueue itself to continue. Doing it here
        # (outside asyncio.run) avoids nesting event loops under eager mode.
        should_resume = asyncio.run(_run())
        if should_resume:
            process_files_async.apply_async(args=[task_id], kwargs={"resumed": True})

    # NOTE: a previous task_failure handler lived here to mark the
    # PreprocessingTask FAILED after retries were exhausted, but Celery's
    # task_failure signal sends ``args`` (not ``body``), so its ``body``
    # guard caused it to return immediately and never run. The global
    # ``mark_failed`` handler in celery/task_signals.py already covers this
    # case correctly (it reads ``args[0]``), so the dead handler was removed.
