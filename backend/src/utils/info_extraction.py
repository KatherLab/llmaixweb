from typing import cast

from llmaix import extract_info as llmaix_extract_info
from openai import OpenAI
from openai.types.chat import ChatCompletionUserMessageParam
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import models


def get_available_models(api_key: str, base_url: str) -> list[str]:
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.models.list()
    return [model.id for model in response.data]


def test_llm_connection(api_key: str, base_url: str, llm_model: str) -> bool:
    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        client.chat.completions.create(
            model=llm_model,
            messages=[ChatCompletionUserMessageParam(role="user", content="Test")],
            max_tokens=1,
        )
        return True
    except Exception as e:
        print(f"Error testing LLM connection: {e}")
        return False


def extract_info(
    trial_id: int,
    document_ids: list[int],
    llm_model: str,
    api_key: str,
    base_url: str,
    schema_id: int,
    db_session: Session,
    project_id: int,
):
    trial: models.Trial = db_session.execute(
        select(models.Trial).where(models.Trial.id == trial_id)
    ).scalar_one_or_none()
    if not trial:
        raise ValueError(f"Trial with ID {trial_id} not found.")

    schema: models.Schema = db_session.execute(
        select(models.Schema).where(models.Schema.id == schema_id)
    ).scalar_one_or_none()
    if not schema:
        raise ValueError(f"Schema with ID {schema_id} not found.")

    documents: list[models.Document] = cast(
        list[models.Document],
        (
            db_session.execute(
                select(models.Document).where(models.Document.id.in_(document_ids))
            )
            .scalars()
            .all()
        ),
    )

    for document in documents:
        try:
            result = llmaix_extract_info(
                prompt=document.text,
                llm_model=llm_model,
                api_key=api_key,
                base_url=base_url,
                json_schema=schema.schema_definition,
            )
            trial_result = models.TrialResult(
                trial_id=trial_id,
                document_id=document.id,
                result=result,
            )
            db_session.add(trial_result)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise e

    trial.status = models.TrialStatus.COMPLETED
    db_session.commit()
