# celery/preprocessing.py

from openai import OpenAI

from .. import models
from ..dependencies import get_db
from ..utils.preprocessing import PreprocessingPipeline
from .celery_config import celery_app

if celery_app:

    @celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
    def process_files_async(
            task_id: int,
            api_key: str | None = None,
            base_url: str | None = None
    ):
        """
        Process files asynchronously with optional API credentials.
        This is the main celery task for the new preprocessing system.
        """
        with next(get_db()) as db:
            pipeline = PreprocessingPipeline(
                db,
                task_id,
                api_key=api_key,
                base_url=base_url
            )
            pipeline.process()

    @celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
    def preprocess_file_celery(
            file_ids: list[int],
            client: OpenAI | None = None,
            base_url: str | None = None,
            api_key: str | None = None,
            pdf_backend: str = "pymupdf4llm",
            ocr_backend: str = "ocrmypdf",
            llm_model: str | None = None,
            use_ocr: bool = True,
            force_ocr: bool = False,
            ocr_languages: list[str] | None = None,
            ocr_model: str | None = None,
            project_id: int | None = None,
            preprocessing_task_id: int | None = None,
            output_file: bool = True,
    ):
        """
        Legacy celery task for backward compatibility.
        Creates a preprocessing configuration and task, then processes files.

        NOTE: table_settings removed - CSV/XLSX settings now come from file_metadata
        """
        with next(get_db()) as db:
            if not project_id:
                raise ValueError("project_id is required")

            # Get or create a configuration for these settings
            config_snapshot = {
                "file_type": models.FileType.MIXED,  # Default to mixed for legacy
                "preprocessing_strategy": models.PreprocessingStrategy.FULL_DOCUMENT,
                "pdf_backend": pdf_backend,
                "ocr_backend": ocr_backend,
                "use_ocr": use_ocr,
                "force_ocr": force_ocr,
                "ocr_languages": ocr_languages,
                "ocr_model": ocr_model,
                "llm_model": llm_model,
                "additional_settings": {
                    "output_file": output_file,
                },
            }

            # Create temporary configuration
            config = models.PreprocessingConfiguration(
                project_id=project_id,
                name=f"Legacy config - {ocr_backend}",
                description="Created from legacy preprocess_file_celery call",
                **{
                    k: v
                    for k, v in config_snapshot.items()
                    if k != "additional_settings"
                },
                additional_settings=config_snapshot.get("additional_settings", {}),
            )
            db.add(config)
            db.commit()
            db.refresh(config)

            # Use existing task or create new one
            if preprocessing_task_id:
                task = db.get(models.PreprocessingTask, preprocessing_task_id)
                if not task:
                    raise ValueError(
                        f"PreprocessingTask {preprocessing_task_id} not found"
                    )
                task.configuration_id = config.id
            else:
                task = models.PreprocessingTask(
                    project_id=project_id,
                    configuration_id=config.id,
                    total_files=len(file_ids),
                    rollback_on_cancel=True,
                )
                db.add(task)

            db.commit()

            # Create file tasks
            for file_id in file_ids:
                file_task = models.FilePreprocessingTask(
                    preprocessing_task_id=task.id, file_id=file_id
                )
                db.add(file_task)

            db.commit()

            # Process using new pipeline with optional API credentials
            pipeline = PreprocessingPipeline(
                db,
                task.id,
                api_key=api_key,
                base_url=base_url
            )

            pipeline.process()

            # Return document IDs for backward compatibility
            db.refresh(task)
            document_ids = []
            for file_task in task.file_tasks:
                document_ids.extend([doc.id for doc in file_task.documents])

            return document_ids
