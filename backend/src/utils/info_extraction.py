import datetime as dt
import json
from sqlite3 import IntegrityError
from typing import Any

import requests
from openai import (
    APIConnectionError,
    APIError,
    AsyncOpenAI,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from sqlalchemy import func, select
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
    except AuthenticationError:
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
    except RateLimitError:
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
    except AuthenticationError:
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
    except AuthenticationError:
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


def test_model_with_schema(
    api_key: str, base_url: str, llm_model: str, schema_definition: dict
) -> dict[str, Any]:
    """Test if a model supports structured output with a specific schema"""
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        # Try to make a minimal completion with structured output
        client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=1,  # Minimal tokens to test
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "test_schema",
                    "schema": schema_definition,
                    "strict": True,
                },
            },
        )

        return {
            "success": True,
            "message": f"Model '{llm_model}' supports structured output with the selected schema.",
            "supports_structured_output": True,
        }
    except Exception as e:
        error_message = str(e)

        # Parse specific error types
        if (
            "json_schema" in error_message.lower()
            or "structured" in error_message.lower()
        ):
            return {
                "success": False,
                "message": f"Model '{llm_model}' does not support structured output or the schema format.",
                "error_type": "structured_output_not_supported",
                "supports_structured_output": False,
            }
        elif "schema" in error_message.lower():
            return {
                "success": False,
                "message": f"Schema validation error: {error_message}",
                "error_type": "schema_validation_error",
                "supports_structured_output": False,
            }
        else:
            # Fall back to general model test
            return test_llm_connection(api_key, base_url, llm_model)


def _now_utc() -> dt.datetime:
    """Return an offset-aware datetime in UTC."""
    return dt.datetime.now(dt.UTC)


def _to_utc(dt_obj: dt.datetime) -> dt.datetime:
    """Return an offset-aware UTC datetime (attach/convert if needed)."""
    if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
        return dt_obj.replace(tzinfo=dt.UTC)
    return dt_obj.astimezone(dt.UTC)


# utils/info_extraction.py
def update_trial_progress(db, trial_id: int) -> None:
    done = db.scalar(
        select(func.count())
        .select_from(models.TrialResult)
        .where(models.TrialResult.trial_id == trial_id)
    )
    trial = db.get(models.Trial, trial_id)
    total = len(trial.document_ids or [])
    progress = done / total if total else 1.0

    trial.docs_done = done
    trial.progress = progress

    # ETA logic - always present and correct
    if trial.started_at and done:
        elapsed = (_now_utc() - _to_utc(trial.started_at)).total_seconds()
        eta = int(elapsed / progress - elapsed) if progress and done < total else 0
        trial.meta = (trial.meta or {}) | {"eta_seconds": eta}
    else:
        trial.meta = (trial.meta or {}) | {"eta_seconds": 0}
    db.commit()


def _build_messages(prompt: models.Prompt, document_text: str) -> list[dict]:
    """Inject the document text into user/system prompt templates."""
    placeholder = "{document_content}"
    msgs: list[dict[str, str]] = []
    if prompt.system_prompt:
        msgs.append(
            {
                "role": "system",
                "content": prompt.system_prompt.replace(placeholder, document_text),
            }
        )
    if prompt.user_prompt:
        msgs.append(
            {
                "role": "user",
                "content": prompt.user_prompt.replace(placeholder, document_text),
            }
        )
    return msgs


def _completion_kwargs(
    model: str, schema_def: dict, messages: list[dict], adv: dict | None
) -> dict:
    kwargs = {
        "model": model,
        "messages": messages,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "extraction_schema",
                "schema": schema_def,
                "strict": True,
            },
        },
    }
    if adv:
        kwargs.update(
            {
                k: v
                for k, v in adv.items()
                if k in {"max_completion_tokens", "temperature"}
            }
        )
    return kwargs


async def extract_info_single_doc_async(
    *,
    client: AsyncOpenAI,
    db_session: Session,
    trial_id: int,
    document_id: int,
    llm_model: str,
    schema_id: int,
    prompt_id: int,
    project_id: int,  # kept for signature parity; not used here
    advanced_options: dict | None = None,
) -> None:
    """Async version used inside the Celery worker."""
    schema: models.Schema = db_session.get(models.Schema, schema_id)
    prompt: models.Prompt = db_session.get(models.Prompt, prompt_id)
    document: models.Document = db_session.get(models.Document, document_id)
    if not (schema and prompt and document):
        raise ValueError("schema / prompt / document not found")

    response = await client.chat.completions.create(
        **_completion_kwargs(
            llm_model,
            schema.schema_definition,
            _build_messages(prompt, document.text),
            advanced_options,
        )
    )
    _store_result(db_session, trial_id, document_id, response)


def extract_info_single_doc(
    *,
    db_session: Session,
    trial_id: int,
    document_id: int,
    llm_model: str,
    api_key: str,
    base_url: str,
    schema_id: int,
    prompt_id: int,
    project_id: int,  # kept for signature parity; not used here
    advanced_options: dict | None = None,
) -> None:
    """Synchronous variant, used when bypass_celery=True."""
    schema: models.Schema = db_session.get(models.Schema, schema_id)
    prompt: models.Prompt = db_session.get(models.Prompt, prompt_id)
    document: models.Document = db_session.get(models.Document, document_id)
    if not (schema and prompt and document):
        raise ValueError("schema / prompt / document not found")

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        **_completion_kwargs(
            llm_model,
            schema.schema_definition,
            _build_messages(prompt, document.text),
            advanced_options,
        )
    )
    _store_result(db_session, trial_id, document_id, response)


def _store_result(db_session, trial_id: int, document_id: int, response) -> None:
    # Skip if a result for this document already exists
    exists = db_session.scalar(
        select(models.TrialResult.id).where(
            models.TrialResult.trial_id == trial_id,
            models.TrialResult.document_id == document_id,
        )
    )
    if exists:
        return

    # Main JSON payload
    result_json = json.loads(response.choices[0].message.content)

    # Optional extra fields
    additional: dict = {}

    # reasoning_content (if present)
    reasoning = getattr(response.choices[0].message, "reasoning_content", None)
    if reasoning is not None:
        additional["reasoning_content"] = reasoning

    # finish_reason (if present)
    finish = getattr(response.choices[0], "finish_reason", None)
    if finish is not None:
        additional["finish_reason"] = finish

    # usage (if present)
    usage = getattr(response, "usage", None)
    if usage is not None:
        # Most OpenAI objects support .model_dump() (pydantic v2) or .dict() (v1)
        if hasattr(usage, "model_dump"):
            additional["usage"] = usage.model_dump()
        elif hasattr(usage, "dict"):
            additional["usage"] = usage.dict()
        else:
            additional["usage"] = {
                k: getattr(usage, k) for k in dir(usage) if not k.startswith("_")
            }

    # Persist the result
    try:
        db_session.add(
            models.TrialResult(
                trial_id=trial_id,
                document_id=document_id,
                result=result_json,
                additional_content=additional,
            )
        )
        db_session.commit()
    except IntegrityError:
        db_session.rollback()
