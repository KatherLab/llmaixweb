import asyncio
import datetime as dt

from .. import models
from ..dependencies import get_db
from ..utils.preprocessing import PreprocessingPipeline
from .celery_config import celery_app

if celery_app:

    @celery_app.task(
        bind=True,
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=3,
        queue="preprocess",
    )
    def process_files_async(
        self,
        task_id: int,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        async def _run():
            failures = {}

            # --- Setup: fetch the task ---
            with next(get_db()) as db:
                task: models.PreprocessingTask = db.get(
                    models.PreprocessingTask, task_id
                )
                if task and (api_key or base_url):
                    if not task.task_metadata:
                        task.task_metadata = {}
                    if api_key:
                        task.task_metadata["api_key"] = api_key
                    if base_url:
                        task.task_metadata["api_base_url"] = base_url
                    db.commit()
                file_tasks = [
                    ft
                    for ft in task.file_tasks
                    if ft.status == models.PreprocessingStatus.PENDING
                ]

            sem = asyncio.Semaphore(5)
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
                            with next(get_db()) as db:
                                _ = db.get(models.PreprocessingTask, task_id)
                                file_task = db.get(
                                    models.FilePreprocessingTask, file_task_id
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
                                pipeline._process_file_task(file_task)

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
                    with next(get_db()) as db:
                        file_task = db.get(models.FilePreprocessingTask, file_task_id)
                        file_task.status = models.PreprocessingStatus.FAILED
                        file_task.error_message = str(exc)
                        file_task.completed_at = dt.datetime.now(dt.UTC)
                        db.commit()

            # --- Launch all file_tasks (concurrent up to limit) ---
            for ft in file_tasks:
                running_tasks[ft.id] = asyncio.create_task(process_file(ft.id))

            # --- Heartbeat: update progress/meta/ETA for frontend ---
            async def progress_heartbeat():
                while True:
                    await asyncio.sleep(3)
                    with next(get_db()) as db:
                        task = db.get(models.PreprocessingTask, task_id)
                        total = len(task.file_tasks)
                        completed = sum(
                            1
                            for f in task.file_tasks
                            if f.status == models.PreprocessingStatus.COMPLETED
                        )
                        failed = sum(
                            1
                            for f in task.file_tasks
                            if f.status == models.PreprocessingStatus.FAILED
                        )
                        cancelled = sum(
                            1
                            for f in task.file_tasks
                            if f.status == models.PreprocessingStatus.CANCELLED
                        )
                        in_progress = sum(
                            1
                            for f in task.file_tasks
                            if f.status == models.PreprocessingStatus.IN_PROGRESS
                        )

                        now = dt.datetime.now(dt.UTC)
                        started = task.started_at or now
                        elapsed = (now - started).total_seconds() if completed else 0
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
                        if all(
                            f.status
                            in [
                                models.PreprocessingStatus.COMPLETED,
                                models.PreprocessingStatus.FAILED,
                                models.PreprocessingStatus.CANCELLED,
                            ]
                            for f in task.file_tasks
                        ):
                            break

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

                total = len(task.file_tasks)
                completed = sum(
                    1
                    for f in task.file_tasks
                    if f.status == models.PreprocessingStatus.COMPLETED
                )
                failed = sum(
                    1
                    for f in task.file_tasks
                    if f.status == models.PreprocessingStatus.FAILED
                )
                cancelled = sum(
                    1
                    for f in task.file_tasks
                    if f.status == models.PreprocessingStatus.CANCELLED
                )

                task.completed_at = now

                if task.is_cancelled:
                    task.status = models.PreprocessingStatus.CANCELLED
                    # Handle keep/delete processed docs on cancel
                    if task.rollback_on_cancel:
                        deleted_count = 0
                        for file_task in task.file_tasks:
                            if file_task.status == models.PreprocessingStatus.COMPLETED:
                                for doc in file_task.documents:
                                    doc.document_sets.clear()
                                    db.delete(doc)
                                    deleted_count += 1
                        task.message = f"Task cancelled and {deleted_count} processed documents rolled back"
                    else:
                        task.message = "Task cancelled, keeping processed documents"
                elif completed == total and total > 0:
                    task.status = models.PreprocessingStatus.COMPLETED
                    task.message = "All files processed successfully."
                elif failed == total:
                    task.status = models.PreprocessingStatus.FAILED
                    task.message = "All files failed to preprocess."
                else:
                    task.status = models.PreprocessingStatus.FAILED
                    task.message = (
                        f"{completed} of {total} files processed successfully, "
                        f"{failed} failed, {cancelled} cancelled."
                    )
                db.commit()

        asyncio.run(_run())
