import datetime as dt
import json
import re
import unicodedata
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

# ------------------------------
# Connection / capability checks
# ------------------------------


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


def get_available_models(api_key: str, base_url: str) -> dict[str, Any]:
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.models.list()
        models_list = [model.id for model in response.data]
        return {
            "success": True,
            "models": models_list,
            "message": f"Successfully loaded {len(models_list)} models",
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
    api_key: str,
    base_url: str,
    llm_model: str,
    schema_definition: dict,
    adv: dict | None = None,
) -> dict[str, Any]:
    """Test if a model supports structured output with a specific schema + optional advanced params."""
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        kwargs: dict[str, Any] = {
            "model": llm_model,
            "messages": [{"role": "user", "content": "Test"}],
            # keep a tiny cap for the probe unless caller explicitly raises it
            "max_tokens": 1,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "test_schema",
                    "schema": schema_definition,
                    "strict": True,
                },
            },
        }

        # Apply advanced params if present
        if adv:
            if "max_completion_tokens" in adv and adv["max_completion_tokens"] is not None:
                # Your API expects max_completion_tokens for completions; override the tiny probe
                kwargs["max_completion_tokens"] = adv["max_completion_tokens"]
                # optional: remove old 'max_tokens' to avoid confusion
                kwargs.pop("max_tokens", None)

            if "temperature" in adv and adv["temperature"] is not None:
                kwargs["temperature"] = adv["temperature"]

            if "reasoning_effort" in adv and adv["reasoning_effort"]:
                kwargs["reasoning_effort"] = adv["reasoning_effort"]
                extra_body = dict(kwargs.get("extra_body") or {})
                allowed = set(extra_body.get("allowed_openai_params", []))
                allowed.add("reasoning_effort")
                extra_body["allowed_openai_params"] = list(allowed)
                kwargs["extra_body"] = extra_body

        client.chat.completions.create(**kwargs)

        return {
            "success": True,
            "message": f"Model '{llm_model}' supports structured output with the selected schema.",
            "supports_structured_output": True,
        }
    except Exception as e:
        error_message = str(e)
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
            return test_llm_connection(api_key, base_url, llm_model)


# ------------------------------
# Time helpers
# ------------------------------


def _now_utc() -> dt.datetime:
    """Return an offset-aware datetime in UTC."""
    return dt.datetime.now(dt.UTC)


def _to_utc(dt_obj: dt.datetime) -> dt.datetime:
    """Return an offset-aware UTC datetime (attach/convert if needed)."""
    if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
        return dt_obj.replace(tzinfo=dt.UTC)
    return dt_obj.astimezone(dt.UTC)


# ------------------------------
# Trial progress
# ------------------------------


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


# ------------------------------
# Input sanitization
# ------------------------------

# Keep only LF (\n). Excludes TAB (\t) and CR (\r) so they can be handled explicitly.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

# Unicode non-characters (optional but harmless)
_NONCHAR_RE = re.compile(
    r"[\uFDD0-\uFDEF\uFFFE\uFFFF"
    r"\U0001FFFE-\U0001FFFF"
    r"\U0002FFFE-\U0002FFFF"
    r"\U0003FFFE-\U0003FFFF"
    r"\U0004FFFE-\U0004FFFF"
    r"\U0005FFFE-\U0005FFFF"
    r"\U0006FFFE-\U0006FFFF"
    r"\U0007FFFE-\U0007FFFF"
    r"\U0008FFFE-\U0008FFFF"
    r"\U0009FFFE-\U0009FFFF"
    r"\U000AFFFE-\U000AFFFF"
    r"\U000BFFFE-\U000BFFFF"
    r"\U000CFFFE-\U000CFFFF"
    r"\U000DFFFE-\U000DFFFF"
    r"\U000EFFFE-\U000EFFFF"
    r"\U0010FFFE-\U0010FFFF]"
)


def sanitize_for_prompt(text: str, *, collapse_space: bool = False) -> str:
    """Hardened sanitizer to prevent raw control chars being copied into JSON."""
    if text is None:
        return ""

    # Ensure it's valid Unicode
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")

    # Normalize (composed form)
    text = unicodedata.normalize("NFC", text)

    # Normalize line endings and tabs *before* control filtering
    text = text.replace("\r", "\n").replace("\t", "    ")

    # Remove dangerous C0 controls except LF (\n)
    text = _CONTROL_CHARS_RE.sub("", text)

    # Strip Unicode non-characters
    text = _NONCHAR_RE.sub("", text)

    # (Optional) tame pathological whitespace
    if collapse_space:
        text = re.sub(r"\n{4,}", "\n\n\n", text)
        text = re.sub(r"[ \t]{3,}", "  ", text)

    return text


# ------------------------------
# Message + request building
# ------------------------------


def _build_messages(prompt: models.Prompt, document_text: str) -> list[dict]:
    """Inject the document text into user/system prompt templates."""
    placeholder = "{document_content}"
    clean_doc = sanitize_for_prompt(document_text, collapse_space=False)

    msgs: list[dict[str, str]] = []
    if prompt.system_prompt:
        msgs.append(
            {
                "role": "system",
                "content": prompt.system_prompt.replace(placeholder, clean_doc),
            }
        )
    if prompt.user_prompt:
        msgs.append(
            {
                "role": "user",
                "content": prompt.user_prompt.replace(placeholder, clean_doc),
            }
        )
    return msgs


def _completion_kwargs(
    model: str, schema_def: dict, messages: list[dict], adv: dict | None
) -> dict:
    """Build kwargs for chat.completions.create, including optional advanced options.

    Supports:
      - max_completion_tokens (int)
      - temperature (float)
      - reasoning_effort ("low" | "medium" | "high")  -> requires extra_body.allowed_openai_params
    """
    kwargs: dict[str, Any] = {
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

    if not adv:
        return kwargs

    # Pass through basic advanced options
    for k in ("max_completion_tokens", "temperature"):
        if k in adv and adv[k] not in (None, ""):
            kwargs[k] = adv[k]

    # Handle reasoning_effort and required extra_body
    if "reasoning_effort" in adv and adv["reasoning_effort"] not in (None, ""):
        kwargs["reasoning_effort"] = adv["reasoning_effort"]

        # Merge/attach extra_body.allowed_openai_params
        extra_body = dict(kwargs.get("extra_body") or {})
        allowed = set(extra_body.get("allowed_openai_params", []))
        allowed.add("reasoning_effort")
        extra_body["allowed_openai_params"] = list(allowed)
        kwargs["extra_body"] = extra_body

        # (Optional) If desired, you could bump max_completion_tokens for "high".
        # Uncomment to enforce a floor only when not set explicitly.
        # if adv["reasoning_effort"] == "high" and "max_completion_tokens" not in kwargs:
        #     kwargs["max_completion_tokens"] = 2048

    return kwargs


# ------------------------------
# Async/sync extraction
# ------------------------------


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


# ------------------------------
# Robust JSON parsing helpers
# ------------------------------

_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def _extract_json_snippet(s: str) -> str:
    """Trim to the first complete top-level JSON object/array; remove code fences."""
    s = _JSON_FENCE_RE.sub("", s.strip())
    first_brace = s.find("{")
    first_brack = s.find("[")
    starts = [x for x in [first_brace, first_brack] if x != -1]
    if not starts:
        return s
    start = min(starts)

    stack: list[str] = []
    i = start
    while i < len(s):
        ch = s[i]
        if ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if not stack or ch != stack[-1]:
                break
            stack.pop()
            if not stack:
                return s[start : i + 1]
        i += 1
    return s[start:]


def _escape_ctrls_in_json_strings(s: str) -> str:
    """Escape raw control characters inside JSON string literals to ....

    Leaves JSON syntax (outside strings) untouched.
    """
    out: list[str] = []
    in_string = False
    escape = False
    quote: str | None = None

    for ch in s:
        if in_string:
            if escape:
                out.append(ch)
                escape = False
                continue
            if ch == "\\":
                out.append(ch)
                escape = True
                continue
            if ch == quote:
                in_string = False
                quote = None
                out.append(ch)
                continue
            code = ord(ch)
            if 0 <= code <= 0x1F or code == 0x7F:
                out.append(f"\\u{code:04x}")
            else:
                out.append(ch)
        else:
            if ch in ('"', "'"):
                in_string = True
                quote = ch
                out.append(ch)
            else:
                out.append(ch)
    return "".join(out)


def safe_json_loads(text: str) -> Any:
    """A tolerant JSON loader for LLM outputs.

    - Tries fast path json.loads first.
    - Removes code fences and trims to a likely JSON snippet.
    - Replaces smart quotes.
    - Escapes raw control chars *inside strings only*.
    """
    try:
        return json.loads(text)
    except Exception:
        pass

    candidate = _extract_json_snippet(text)
    candidate = candidate.replace("“", '"').replace("”", '"').replace("’", "'")
    candidate = _escape_ctrls_in_json_strings(candidate)
    return json.loads(candidate)


# ------------------------------
# Store result
# ------------------------------


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

    raw_content = response.choices[0].message.content

    # Parse JSON robustly
    try:
        result_json = safe_json_loads(raw_content)
    except Exception as e:
        # Record the failure but don't crash the whole trial; persist raw for later inspection
        additional: dict[str, Any] = {"json_error": str(e), "raw_response": raw_content}
        try:
            reasoning = getattr(response.choices[0].message, "reasoning_content", None)
            if reasoning is not None:
                additional["reasoning_content"] = reasoning
            finish = getattr(response.choices[0], "finish_reason", None)
            if finish is not None:
                additional["finish_reason"] = finish
            usage = getattr(response, "usage", None)
            if usage is not None:
                if hasattr(usage, "model_dump"):
                    additional["usage"] = usage.model_dump()
                elif hasattr(usage, "dict"):
                    additional["usage"] = usage.dict()
                else:
                    additional["usage"] = {
                        k: getattr(usage, k)
                        for k in dir(usage)
                        if not k.startswith("_")
                    }
        except Exception:
            pass

        try:
            db_session.add(
                models.TrialResult(
                    trial_id=trial_id,
                    document_id=document_id,
                    result=None,
                    additional_content=additional,
                )
            )
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
        # Re-raise so the caller's failure accounting still works
        raise

    # If we got here, parsing succeeded; collect additional metadata
    additional: dict[str, Any] = {}
    reasoning = getattr(response.choices[0].message, "reasoning_content", None)
    if reasoning is not None:
        additional["reasoning_content"] = reasoning
    finish = getattr(response.choices[0], "finish_reason", None)
    if finish is not None:
        additional["finish_reason"] = finish
    usage = getattr(response, "usage", None)
    if usage is not None:
        if hasattr(usage, "model_dump"):
            additional["usage"] = usage.model_dump()
        elif hasattr(usage, "dict"):
            additional["usage"] = usage.dict()
        else:
            additional["usage"] = {
                k: getattr(usage, k) for k in dir(usage) if not k.startswith("_")
            }

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
