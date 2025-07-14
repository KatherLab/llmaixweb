from typing import Any, cast

import requests
from llmaix import extract_info as llmaix_extract_info
from openai import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from openai.types.chat import ChatCompletionUserMessageParam
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models


# Add this missing function back
def test_llm_connection(api_key: str, base_url: str, llm_model: str) -> dict[str, Any]:
    """Test LLM connection with a specific model by making a test completion"""
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=1,
        )
        return {"success": True, "message": "Model test successful"}
    except AuthenticationError as e:
        return {
            "success": False,
            "message": "Authentication failed. Please check your API key.",
            "error_type": "authentication",
        }
    except APIConnectionError as e:
        return {
            "success": False,
            "message": f"Connection failed. Please check your base URL: {str(e)}",
            "error_type": "connection",
        }
    except RateLimitError as e:
        return {
            "success": False,
            "message": "Rate limit exceeded. Please try again later.",
            "error_type": "rate_limit",
        }
    except APIError as e:
        error_message = str(e)
        if "model" in error_message.lower() and "not found" in error_message.lower():
            return {
                "success": False,
                "message": f"Model '{llm_model}' is not available. Please select a different model.",
                "error_type": "model_not_found",
            }
        else:
            return {
                "success": False,
                "message": f"API error: {error_message}",
                "error_type": "api_error",
            }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "message": "Connection refused. Please check if the base URL is correct and the service is running.",
            "error_type": "connection_refused",
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "Connection timeout. The service might be slow or unavailable.",
            "error_type": "timeout",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "error_type": "unknown",
        }


# Update your existing functions to return detailed responses
def get_available_models(api_key: str, base_url: str) -> dict[str, Any]:
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.models.list()
        models = [model.id for model in response.data]
        return {
            "success": True,
            "models": models,
            "message": f"Successfully loaded {len(models)} models",
        }
    except AuthenticationError as e:
        return {
            "success": False,
            "models": [],
            "message": "Authentication failed. Please check your API key.",
            "error_type": "authentication",
        }
    except APIConnectionError as e:
        return {
            "success": False,
            "models": [],
            "message": f"Connection failed. Please check your base URL: {str(e)}",
            "error_type": "connection",
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "models": [],
            "message": "Connection refused. Please check if the base URL is correct and the service is running.",
            "error_type": "connection_refused",
        }
    except Exception as e:
        return {
            "success": False,
            "models": [],
            "message": f"Failed to load models: {str(e)}",
            "error_type": "model_loading_failed",
        }


def test_api_connection(api_key: str, base_url: str) -> dict[str, Any]:
    """Test API connection by trying to list models"""
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.models.list()
        return {
            "success": True,
            "message": "API connection successful",
            "models_count": len(response.data),
        }
    except AuthenticationError as e:
        return {
            "success": False,
            "message": "Authentication failed. Please check your API key.",
            "error_type": "authentication",
        }
    except APIConnectionError as e:
        return {
            "success": False,
            "message": f"Connection failed. Please check your base URL: {str(e)}",
            "error_type": "connection",
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "message": "Connection refused. Please check if the base URL is correct and the service is running.",
            "error_type": "connection_refused",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "error_type": "unknown",
        }


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
