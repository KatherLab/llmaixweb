from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .... import models
from ....core.config import settings
from ....core.security import get_current_user
from ....dependencies import get_db
from ....utils.helpers import test_remote_image_support
from ....utils.info_extraction import (
    get_available_models,
    test_api_connection,
    test_llm_connection,
    test_model_with_schema,
)

router = APIRouter()


@router.get("/models", response_model=dict[str, Any])
def get_available_llm_models(
    api_key: str | None = settings.OPENAI_API_KEY,
    base_url: str | None = settings.OPENAI_API_BASE,
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    if api_key is None or base_url is None:
        return {
            "success": False,
            "models": [],
            "message": "LLM configuration is incomplete",
            "error_type": "incomplete_config",
        }
    return get_available_models(api_key, base_url)


@router.post("/test-connection", response_model=dict[str, Any])
def test_api_connection_endpoint(
    api_key: str | None = settings.OPENAI_API_KEY,
    base_url: str | None = settings.OPENAI_API_BASE,
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    if api_key is None or base_url is None:
        return {
            "success": False,
            "message": "LLM configuration is incomplete. Please provide API key and base URL.",
            "error_type": "incomplete_config",
        }
    return test_api_connection(api_key, base_url)


@router.post("/test-model", response_model=dict[str, Any])
def test_llm_model_endpoint(
    api_key: str | None = settings.OPENAI_API_KEY,
    base_url: str | None = settings.OPENAI_API_BASE,
    llm_model: str | None = settings.OPENAI_API_MODEL,
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    if api_key is None or base_url is None or llm_model is None:
        return {
            "success": False,
            "message": "LLM configuration is incomplete. Please provide API key, base URL, and model.",
            "error_type": "incomplete_config",
        }
    return test_llm_connection(api_key, base_url, llm_model)


@router.post("/test-model-schema", response_model=dict[str, Any])
def test_model_with_schema_endpoint(
    api_key: str | None = settings.OPENAI_API_KEY,
    base_url: str | None = settings.OPENAI_API_BASE,
    llm_model: str | None = settings.OPENAI_API_MODEL,
    schema_id: int | None = None,
    max_completion_tokens: int | None = None,
    temperature: float | None = None,
    reasoning_effort: str | None = None,  # "low" | "medium" | "high"
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Test if a model supports structured output with a specific schema"""
    if api_key is None or base_url is None or llm_model is None:
        return {
            "success": False,
            "message": "LLM configuration is incomplete. Please provide API key, base URL, and model.",
            "error_type": "incomplete_config",
        }

    if schema_id is None:
        return {
            "success": False,
            "message": "Schema ID is required for testing structured output.",
            "error_type": "missing_schema",
        }

    # Get the schema
    schema = db.execute(
        select(models.Schema).where(models.Schema.id == schema_id)
    ).scalar_one_or_none()

    if not schema:
        return {
            "success": False,
            "message": "Schema not found.",
            "error_type": "schema_not_found",
        }

    adv: dict[str, Any] = {}
    if max_completion_tokens is not None:
        adv["max_completion_tokens"] = max_completion_tokens
    if temperature is not None:
        adv["temperature"] = temperature
    if reasoning_effort:
        adv["reasoning_effort"] = reasoning_effort

    # Test the model with structured output
    return test_model_with_schema(
        api_key, base_url, llm_model, schema.schema_definition, adv or None
    )


@router.get("/test-vlm-image-support")
def test_vlm_image_support(
    *,
    db: Session = Depends(get_db),
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """
    Test if a VLM model supports image input.
    All params are optional (except model).
    """

    # Use default settings if not provided
    api_key = api_key or settings.OPENAI_API_KEY
    base_url = base_url or settings.OPENAI_API_BASE

    if not api_key or not base_url or not model:
        return {
            "supported": False,
            "message": "Configuration incomplete: api_key, base_url, and model are required",
        }

    try:
        api_url = base_url
        if not api_url.endswith("/chat/completions"):
            api_url = api_url.rstrip("/") + "/chat/completions"

        supported = test_remote_image_support(
            api_url=api_url, model=model, api_key=api_key
        )

        return {
            "supported": supported,
            "message": "Model supports image input"
            if supported
            else "Model does not support image input",
        }
    except Exception as e:
        return {"supported": False, "message": f"Test failed: {str(e)}"}
