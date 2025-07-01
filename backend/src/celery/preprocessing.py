from openai import OpenAI

from .. import models
from ..dependencies import get_db
from ..utils.preprocessing import preprocess_files
from .celery_config import celery_app

if celery_app:

    @celery_app.task(autoretry_for=(Exception,), retry_backoff=True)
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
        with next(get_db()) as db_session:
            files = (
                db_session.query(models.File).filter(models.File.id.in_(file_ids)).all()
            )
            return preprocess_files(
                files=files,
                client=client,
                ocr_backend=ocr_backend,
                pdf_backend=pdf_backend,
                llm_model=llm_model,
                use_ocr=use_ocr,
                force_ocr=force_ocr,
                ocr_languages=ocr_languages,
                ocr_model=ocr_model,
                base_url=base_url,
                api_key=api_key,
                db_session=db_session,
                project_id=project_id,
                preprocessing_task_id=preprocessing_task_id,
                output_file=output_file,
            )
