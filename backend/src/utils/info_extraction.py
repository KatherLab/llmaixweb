import json
from typing import Any, cast

import requests
from openai import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
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
        response = client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "user", "content": "Test"}
            ],
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


def extract_info(
        trial_id: int,
        document_ids: list[int],
        llm_model: str,
        api_key: str,
        base_url: str,
        schema_id: int,
        prompt_id: int,
        db_session: Session,
        project_id: int,
        advanced_options: dict | None = None,
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

    prompt: models.Prompt = db_session.execute(
        select(models.Prompt).where(models.Prompt.id == prompt_id)
    ).scalar_one_or_none()
    if not prompt:
        raise ValueError(f"Prompt with ID {prompt_id} not found.")

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
            # Replace the placeholder with document content
            placeholder = "{document_content}"

            # Prepare the messages for the LLM
            messages = []

            # Add system prompt if exists
            if prompt.system_prompt:
                system_content = prompt.system_prompt.replace(placeholder, document.text)
                messages.append({"role": "system", "content": system_content})

            # Add user prompt if exists
            if prompt.user_prompt:
                user_content = prompt.user_prompt.replace(placeholder, document.text)
                messages.append({"role": "user", "content": user_content})

            # Use OpenAI client directly for structured output
            client = OpenAI(api_key=api_key, base_url=base_url)

            completion_kwargs = {
                "model": llm_model,
                "messages": messages,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "extraction_schema",
                        "schema": schema.schema_definition,
                        "strict": True,
                    },
                },
            }

            # Add advanced options if provided
            if advanced_options:
                if "max_completion_tokens" in advanced_options:
                    completion_kwargs["max_completion_tokens"] = advanced_options[
                        "max_completion_tokens"
                    ]
                # TODO: Add more advanced options here in the future

            response = client.chat.completions.create(**completion_kwargs)

            result = json.loads(response.choices[0].message.content)

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
