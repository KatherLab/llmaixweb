from .. import models
from ..dependencies import get_db
from ..utils.preprocessing import PreprocessingPipeline
from .celery_config import celery_app

if celery_app:

    @celery_app.task(
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=3,
        queue="preprocess",  # heavy OCR queue
    )
    def process_files_async(
        task_id: int,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """
        Process files asynchronously with optional API credentials.
        """
        with next(get_db()) as db:
            # --- (existing body remains unchanged) ---
            # Get task and update metadata with API credentials
            task = db.get(models.PreprocessingTask, task_id)
            if task and (api_key or base_url):
                if not task.task_metadata:
                    task.task_metadata = {}
                if api_key:
                    task.task_metadata["api_key"] = api_key
                if base_url:
                    task.task_metadata["api_base_url"] = base_url
                db.commit()

            pipeline = PreprocessingPipeline(
                db,
                task_id,
                api_key=api_key,
                base_url=base_url,
            )
            pipeline.process()
