from ..dependencies import get_db
from ..utils.info_extraction import extract_info
from .celery_config import celery_app

if celery_app:

    @celery_app.task(autoretry_for=(Exception,), retry_backoff=True)
    def extract_info_celery(
        trial_id: int,
        document_ids: list[int],
        llm_model: str,
        api_key: str,
        base_url: str,
        schema_id: int,
        prompt_id: int,
        project_id: int,
        advanced_options: dict | None = None,
    ):
        with next(get_db()) as db_session:
            extract_info(
                trial_id=trial_id,
                document_ids=document_ids,
                llm_model=llm_model,
                api_key=api_key,
                base_url=base_url,
                schema_id=schema_id,
                prompt_id=prompt_id,
                db_session=db_session,
                project_id=project_id,
                advanced_options=advanced_options,
            )
