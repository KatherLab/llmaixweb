from celery import Celery
from ..utils.info_extraction import extract_info

app = Celery("info_extraction", broker="redis://localhost:6379/0")


@app.task
def extract_info_celery(
    trial_id: int,
    document_ids: list[int],
    llm_model: str,
    api_key: str,
    base_url: str,
    schema_id: int,
    db_session,
    project_id: int,
):
    extract_info(
        trial_id=trial_id,
        document_ids=document_ids,
        llm_model=llm_model,
        api_key=api_key,
        base_url=base_url,
        schema_id=schema_id,
        db_session=db_session,
        project_id=project_id,
    )
