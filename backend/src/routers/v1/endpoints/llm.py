# backend/src/routers/v1/endpoints/llm.py
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .... import models
from ....core.config import settings
from ....core.security import can_access_project, get_current_user
from ....dependencies import get_db
from ....middleware.error_handlers import record_internal_error
from ....schemas.other import (
    LLMConnectionRequest,
    LLMModelSchemaTestRequest,
    LLMModelTestRequest,
    LLMVlmImageSupportRequest,
)
from ....utils.helpers import test_remote_image_support
from ....utils.info_extraction import (
    get_available_models,
    test_api_connection,
    test_llm_connection,
    test_model_with_schema,
)
from ....utils.url_safety import UnsafeEndpointError, validate_user_endpoint

router = APIRouter()


def _resolve_creds(
    api_key: str | None, base_url: str | None
) -> tuple[str | None, str | None]:
    """Fall back to the system-wide configured LLM credentials when not supplied."""
    return api_key or settings.OPENAI_API_KEY, base_url or settings.OPENAI_API_BASE


def _invalid_url_response(
    message: str = "The provided endpoint URL is not allowed.",
) -> dict[str, Any]:
    """Safe, category-only response for a blocked user-supplied endpoint (SSRF)."""
    return {"success": False, "message": message, "error_type": "invalid_url"}


@router.post("/models", response_model=dict[str, Any])
def get_available_llm_models(
    body: LLMConnectionRequest | None = None,
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    user_base_url = (body.base_url if body else None) or settings.OPENAI_API_BASE
    try:
        user_base_url = validate_user_endpoint(user_base_url)
    except UnsafeEndpointError:
        # Include an empty `models` list so the response still satisfies the
        # frontend LlmModelsResponse contract (models: string[]).
        return _invalid_url_response() | {"models": []}
    api_key, base_url = _resolve_creds((body.api_key if body else None), user_base_url)
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
    body: LLMConnectionRequest | None = None,
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    user_base_url = (body.base_url if body else None) or settings.OPENAI_API_BASE
    try:
        user_base_url = validate_user_endpoint(user_base_url)
    except UnsafeEndpointError:
        return _invalid_url_response()
    api_key, base_url = _resolve_creds((body.api_key if body else None), user_base_url)
    if api_key is None or base_url is None:
        return {
            "success": False,
            "message": "LLM configuration is incomplete. Please provide API key and base URL.",
            "error_type": "incomplete_config",
        }
    return test_api_connection(api_key, base_url)


@router.post("/test-model", response_model=dict[str, Any])
def test_llm_model_endpoint(
    body: LLMModelTestRequest | None = None,
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    user_base_url = (body.base_url if body else None) or settings.OPENAI_API_BASE
    try:
        user_base_url = validate_user_endpoint(user_base_url)
    except UnsafeEndpointError:
        return _invalid_url_response()
    api_key, base_url = _resolve_creds((body.api_key if body else None), user_base_url)
    llm_model = (body.llm_model if body else None) or settings.OPENAI_API_MODEL
    if api_key is None or base_url is None or llm_model is None:
        return {
            "success": False,
            "message": "LLM configuration is incomplete. Please provide API key, base URL, and model.",
            "error_type": "incomplete_config",
        }
    return test_llm_connection(api_key, base_url, llm_model)


@router.post("/test-model-schema", response_model=dict[str, Any])
def test_model_with_schema_endpoint(
    body: LLMModelSchemaTestRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Test if a model supports structured output with a specific schema"""
    try:
        user_base_url = validate_user_endpoint(
            body.base_url or settings.OPENAI_API_BASE
        )
    except UnsafeEndpointError:
        return _invalid_url_response()
    api_key, base_url = _resolve_creds(body.api_key, user_base_url)
    llm_model = body.llm_model or settings.OPENAI_API_MODEL
    if api_key is None or base_url is None or llm_model is None:
        return {
            "success": False,
            "message": "LLM configuration is incomplete. Please provide API key, base URL, and model.",
            "error_type": "incomplete_config",
        }

    if body.schema_id is None:
        return {
            "success": False,
            "message": "Schema ID is required for testing structured output.",
            "error_type": "missing_schema",
        }

    # Verify the caller owns the project before reading its schema (the router
    # is not nested under /{project_id}, so scope explicitly to avoid leaking
    # another project's schema_definition).
    project = db.execute(
        select(models.Project).where(models.Project.id == body.project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(current_user, project):
        raise HTTPException(status_code=403, detail="Not authorized")

    schema = db.execute(
        select(models.Schema).where(
            models.Schema.id == body.schema_id,
            models.Schema.project_id == body.project_id,
        )
    ).scalar_one_or_none()

    if not schema:
        return {
            "success": False,
            "message": "Schema not found.",
            "error_type": "schema_not_found",
        }

    adv: dict[str, Any] = {}
    if body.max_completion_tokens is not None:
        adv["max_completion_tokens"] = body.max_completion_tokens
    if body.temperature is not None:
        adv["temperature"] = body.temperature
    if body.reasoning_effort:
        adv["reasoning_effort"] = body.reasoning_effort

    # Test the model with structured output
    return test_model_with_schema(
        api_key, base_url, llm_model, schema.schema_definition, adv or None
    )


@router.post("/test-vlm-image-support")
def test_vlm_image_support(
    body: LLMVlmImageSupportRequest | None = None,
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """
    Test if a VLM model supports image input.
    All credential fields are optional and fall back to system defaults.
    """
    user_base_url = (body.base_url if body else None) or settings.OPENAI_API_BASE
    try:
        user_base_url = validate_user_endpoint(user_base_url)
    except UnsafeEndpointError:
        return {
            "supported": False,
            "message": "The provided endpoint URL is not allowed.",
        }
    api_key, base_url = _resolve_creds((body.api_key if body else None), user_base_url)
    model = body.llm_model if body else None

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
        # Don't echo the upstream exception string — it can embed the response
        # body/URL of an internal service the user pointed base_url at (SSRF
        # exfiltration channel). Record it server-side under a correlation id
        # (so an admin can diagnose) and return a category-only message + id.
        error_id = record_internal_error(e, actor=current_user)
        return {
            "supported": False,
            "message": f"Image support test failed. (error id: {error_id})",
            "error_id": error_id,
        }
