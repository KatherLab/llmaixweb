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
    project_id: int,
    advanced_options: dict | None = None,
) -> None:
    schema: models.Schema = db_session.get(models.Schema, schema_id)
    prompt: models.Prompt = db_session.get(models.Prompt, prompt_id)
    document: models.Document = db_session.get(models.Document, document_id)
    if not (schema and prompt and document):
        raise ValueError("schema / prompt / document not found")

    kwargs = _completion_kwargs(
        llm_model,
        schema.schema_definition,
        _build_messages(prompt, document.text),
        advanced_options,
    )
    response = await client.chat.completions.create(**kwargs)

    finish_reason = getattr(response.choices[0], "finish_reason", None)
    raw_content = response.choices[0].message.content
    has_reasoning = bool(getattr(response.choices[0].message, "reasoning_content", None))

    if (finish_reason == "length") and (raw_content is None or (isinstance(raw_content, str) and raw_content.strip() == "")):
        bumped_adv = _bump_for_length(advanced_options, getattr(response, "usage", None), has_reasoning)
        bumped_kwargs = _completion_kwargs(
            llm_model,
            schema.schema_definition,
            _build_messages(prompt, document.text),
            bumped_adv,
        )
        response = await client.chat.completions.create(**bumped_kwargs)

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
    project_id: int,
    advanced_options: dict | None = None,
) -> None:
    schema: models.Schema = db_session.get(models.Schema, schema_id)
    prompt: models.Prompt = db_session.get(models.Prompt, prompt_id)
    document: models.Document = db_session.get(models.Document, document_id)
    if not (schema and prompt and document):
        raise ValueError("schema / prompt / document not found")

    client = OpenAI(api_key=api_key, base_url=base_url)

    kwargs = _completion_kwargs(
        llm_model,
        schema.schema_definition,
        _build_messages(prompt, document.text),
        advanced_options,
    )
    response = client.chat.completions.create(**kwargs)

    finish_reason = getattr(response.choices[0], "finish_reason", None)
    raw_content = response.choices[0].message.content
    has_reasoning = bool(getattr(response.choices[0].message, "reasoning_content", None))

    if (finish_reason == "length") and (raw_content is None or (isinstance(raw_content, str) and raw_content.strip() == "")):
        bumped_adv = _bump_for_length(advanced_options, getattr(response, "usage", None), has_reasoning)
        bumped_kwargs = _completion_kwargs(
            llm_model,
            schema.schema_definition,
            _build_messages(prompt, document.text),
            bumped_adv,
        )
        response = client.chat.completions.create(**bumped_kwargs)

    _store_result(db_session, trial_id, document_id, response)


# ------------------------------
# Robust JSON parsing helpers
# ------------------------------

_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def _extract_json_snippet(s: str) -> str:
    """Trim to the first complete top-level JSON object/array; remove code fences."""
    # Be tolerant to None and non-strings
    if not isinstance(s, str):
        s = "" if s is None else str(s)

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
    """A tolerant JSON loader for LLM outputs."""
    # Be tolerant to None and non-strings early
    if text is None:
        text = ""
    elif not isinstance(text, str):
        text = str(text)

    # Fast path
    try:
        return json.loads(text)
    except Exception:
        pass

    # Heuristic recovery
    candidate = _extract_json_snippet(text)
    candidate = candidate.replace("“", '"').replace("”", '"').replace("’", "'")
    candidate = _escape_ctrls_in_json_strings(candidate)
    return json.loads(candidate)


# ------------------------------
# Finish-reason handling & user guidance
# ------------------------------

class IncompleteLLMResponseError(RuntimeError):
    """Raised when the model did not finish with 'stop' and we don't have a safely parsable result."""
    def __init__(self, technical_message: str, user_message: str | None = None):
        super().__init__(technical_message)
        self.user_message = user_message or technical_message


def _analyze_truncation(s: str, tail_len: int = 240) -> dict[str, Any]:
    """
    Heuristically detect if `s` looks truncated or empty:
    - Empty output (no content)
    - Unbalanced braces/brackets/quotes
    - Ends mid-token
    Returns flags + a tail snippet for UI/help.
    """
    # Normalize non-string input
    if not isinstance(s, str):
        s = "" if s is None else str(s)

    if s.strip() == "":
        return {
            "empty_output": True,
            "likely_truncated": True,  # treat as truncated when finish_reason != stop
            "unclosed_string": False,
            "unclosed_braces": 0,
            "unclosed_brackets": 0,
            "tail_snippet": "",
        }

    tail = s[-tail_len:]
    braces = brackets = 0
    in_str = False
    esc = False
    quote = None
    for ch in s:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                in_str = False
                quote = None
        else:
            if ch in ("'", '"'):
                in_str = True
                quote = ch
            elif ch == "{":
                braces += 1
            elif ch == "}":
                braces -= 1
            elif ch == "[":
                brackets += 1
            elif ch == "]":
                brackets -= 1

    likely_unclosed_string = in_str
    likely_unclosed_braces = braces > 0
    likely_unclosed_brackets = brackets > 0

    ends_cleanly = s.rstrip().endswith(("}", "]"))
    likely_truncated = (not ends_cleanly) or likely_unclosed_string or likely_unclosed_braces or likely_unclosed_brackets

    return {
        "empty_output": False,
        "likely_truncated": bool(likely_truncated),
        "unclosed_string": bool(likely_unclosed_string),
        "unclosed_braces": braces if braces > 0 else 0,
        "unclosed_brackets": brackets if brackets > 0 else 0,
        "tail_snippet": tail,
    }


def _advice_for_finish_reason(
    *,
    finish_reason: str | None,
    usage: Any | None,
    advanced_options: dict | None,
    has_reasoning: bool,
) -> dict[str, Any]:
    """
    Build actionable advice for callers/UX.
    - Suggest raising max_completion_tokens if we hit length or usage shows we're near limits.
    - Suggest lowering reasoning_effort if using 'high' and content is long.
    - Provide other finish_reason-specific hints.
    """
    advice: dict[str, Any] = {"recommendations": [], "context": {}}
    adv = advanced_options or {}
    current_max_tok = adv.get("max_completion_tokens")
    reasoning_effort = adv.get("reasoning_effort")
    temperature = adv.get("temperature")

    comp_toks = getattr(usage, "completion_tokens", None) if usage is not None else None
    prompt_toks = getattr(usage, "prompt_tokens", None) if usage is not None else None
    total_toks = getattr(usage, "total_tokens", None) if usage is not None else None

    advice["context"]["usage"] = {
        "prompt_tokens": prompt_toks,
        "completion_tokens": comp_toks,
        "total_tokens": total_toks,
    }
    advice["context"]["advanced_options"] = {
        "max_completion_tokens": current_max_tok,
        "reasoning_effort": reasoning_effort,
        "temperature": temperature,
    }

    def bump_target():
        if isinstance(comp_toks, int) and comp_toks > 0:
            return min(comp_toks * 2, comp_toks + 4096)
        return 2048 if not current_max_tok else int(current_max_tok * 2)

    if finish_reason == "length":
        advice["recommendations"].append(
            {
                "action": "increase_max_completion_tokens",
                "suggested_value": bump_target(),
                "rationale": "Model stopped due to length; completion likely truncated.",
            }
        )
        if reasoning_effort in {"high", "medium"} and has_reasoning:
            advice["recommendations"].append(
                {
                    "action": "lower_reasoning_effort",
                    "suggested_value": "low" if reasoning_effort == "high" else "low",
                    "rationale": "Reasoning traces are long and consume tokens; lowering can prevent cutoffs.",
                }
            )
        advice["recommendations"].append(
            {
                "action": "reduce_output_size",
                "rationale": "Consider a leaner schema or more targeted prompt to reduce required tokens.",
            }
        )
        advice["recommendations"].append(
            {
                "action": "lower_temperature",
                "rationale": "Lowering temperature can reduce verbosity in some models.",
            }
        )

    elif finish_reason == "content_filter":
        advice["recommendations"].append(
            {
                "action": "adjust_prompt_or_redact",
                "rationale": "Content may have triggered safety filters; sanitize inputs or rephrase prompt.",
            }
        )

    elif finish_reason and finish_reason != "stop":
        advice["recommendations"].append(
            {
                "action": "retry_or_adjust_parameters",
                "rationale": f"Non-stop finish reason '{finish_reason}'. Consider retrying with more tokens or fewer constraints.",
            }
        )

    if isinstance(total_toks, int) and isinstance(prompt_toks, int) and current_max_tok:
        if (total_toks - prompt_toks) >= int(0.9 * int(current_max_tok)):
            advice["recommendations"].append(
                {
                    "action": "raise_max_completion_tokens",
                    "suggested_value": bump_target(),
                    "rationale": "Observed completion tokens were ~90%+ of the cap.",
                }
            )

    return advice


def _format_reco(action: str, suggested_value) -> str:
    if suggested_value is None or suggested_value == "":
        return f"- {action.replace('_', ' ').capitalize()}."
    return f"- {action.replace('_', ' ').capitalize()}: {suggested_value}"


def _suggestion_phrase(action: str, suggested_value) -> str:
    """Turn a recommendation into a short, actionable phrase for UI toasts."""
    a = (action or "").lower()

    if a in {"increase_max_completion_tokens", "raise_max_completion_tokens"}:
        if suggested_value not in (None, ""):
            return f"increase max_completion_tokens to {suggested_value}"
        return "increase max_completion_tokens"

    if a == "lower_reasoning_effort":
        if suggested_value not in (None, ""):
            return f"set reasoning_effort={suggested_value}"
        return "lower reasoning_effort"

    if a == "reduce_output_size":
        return "reduce output size (leaner schema or shorter fields)"

    if a == "lower_temperature":
        return "lower temperature"

    if a == "adjust_prompt_or_redact":
        return "sanitize/redact inputs or rephrase prompt"

    if a == "retry_or_adjust_parameters":
        return "retry with more tokens or fewer constraints"

    # Fallback
    if suggested_value not in (None, ""):
        return f"{a.replace('_', ' ')} to {suggested_value}"
    return a.replace("_", " ")


def _summarize_recommendations_for_message(recos: list[dict], max_items: int = 3) -> str:
    """Condense a list of recommendations into a short 'Try: ...; ...; ...' string."""
    phrases: list[str] = []
    for r in recos or []:
        phrases.append(_suggestion_phrase(r.get("action"), r.get("suggested_value")))
    # Deduplicate while preserving order
    seen = set()
    uniq = []
    for p in phrases:
        if p and p not in seen:
            uniq.append(p)
            seen.add(p)
    return "; ".join(uniq[:max_items])


def _build_user_guidance(
    *,
    finish_reason: str | None,
    truncation: dict[str, Any] | None,
    advice: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Make a user-friendly guidance payload with:
      - title
      - what_happened
      - how_to_fix (bulleted suggestions)
      - details (optional tail snippet for support/debug)
      - user_message (single-line summary with concrete suggestions if available)
    """
    fr = (finish_reason or "").lower()
    title = "The model stopped early"

    empty_output = bool(truncation.get("empty_output")) if truncation else False
    if fr == "length":
        title = "Your result was cut off (token limit reached)"
    elif fr == "content_filter":
        title = "The output was blocked by a content filter"
    elif fr and fr != "stop":
        title = f"Model stopped with '{fr}'"

    # What happened
    if empty_output:
        what = (
            "The model produced no JSON content. It likely used the available tokens for reasoning "
            "and hit the completion cap before emitting any structured output."
        )
    elif fr == "length":
        what = (
            "The model hit its completion token limit before finishing the JSON output, "
            "so the result is incomplete."
        )
    elif fr == "content_filter":
        what = (
            "The provider’s safety system blocked part of the response. "
            "This often happens if the prompt or document contains sensitive or disallowed content."
        )
    elif fr and fr != "stop":
        what = "The model ended unexpectedly and may not have produced a complete result."
    else:
        what = "The model didn’t finish generating the full structured result."

    # How to fix
    how_to_fix: list[str] = []
    recos = []
    if advice and isinstance(advice.get("recommendations"), list):
        recos = advice["recommendations"]
        for reco in recos:
            how_to_fix.append(
                _format_reco(reco.get("action", "adjust settings"), reco.get("suggested_value"))
            )

    if truncation and truncation.get("likely_truncated"):
        how_to_fix.append("- Reduce output size (leaner schema, shorter descriptions) or split documents.")

    details = {}
    if truncation:
        tail = truncation.get("tail_snippet")
        if tail:
            details["tail_snippet"] = tail

    # Build short advice summary for toast/snackbar
    advice_summary = _summarize_recommendations_for_message(recos, max_items=3)
    if advice_summary:
        user_message = f"{title} — Try: {advice_summary}"
    else:
        user_message = title + " — " + (
            "Try increasing max completion tokens or lowering reasoning effort." if fr == "length"
            else "Try adjusting settings or sanitizing the input."
        )

    return {
        "title": title,
        "what_happened": what,
        "how_to_fix": how_to_fix,
        "details": details,
        "user_message": user_message,
    }


def _bump_for_length(adv: dict | None, usage: Any | None, has_reasoning: bool) -> dict:
    """
    Return a bumped advanced_options dict for a retry after a 'length' stop with empty content.

    Changes:
      - Preserves the SAME reasoning_effort if the caller set one (no automatic lowering).
      - Doubles max_completion_tokens (or sets a floor) with a hard +4096 cap over current.
      - Leaves temperature as-is; if unset, defaults to 0 to encourage concise output.

    Notes:
      - We still accept `has_reasoning` for future heuristics, but we do NOT change reasoning_effort here.
    """
    new_adv = dict(adv or {})

    # Current cap (default floor if absent)
    current_cap = int(new_adv.get("max_completion_tokens") or 2048)

    # Heuristic bump target based on observed completion tokens when available
    comp_toks = getattr(usage, "completion_tokens", None) if usage is not None else None
    if isinstance(comp_toks, int) and comp_toks > 0:
        suggested = min(comp_toks * 2, comp_toks + 4096)
    else:
        suggested = min(current_cap * 2, current_cap + 4096)

    new_adv["max_completion_tokens"] = max(suggested, current_cap)

    # Preserve existing reasoning_effort EXACTLY as provided by the caller; do not modify.
    # (If none was set originally, we leave it unset.)

    # Keep existing temperature; if not provided, default to 0 for brevity.
    if "temperature" not in new_adv or new_adv["temperature"] in (None, ""):
        new_adv["temperature"] = 0

    return new_adv


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

    # Pull raw values first
    raw_content = response.choices[0].message.content
    reasoning = getattr(response.choices[0].message, "reasoning_content", None)
    finish_reason = getattr(response.choices[0], "finish_reason", None)
    usage = getattr(response, "usage", None)

    # Common additional payload we’ll enrich across branches
    additional: dict[str, Any] = {}
    if reasoning is not None:
        additional["reasoning_content"] = reasoning
    if finish_reason is not None:
        additional["finish_reason"] = finish_reason
    if usage is not None:
        try:
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

    # Prepare truncation + advice + user guidance for any non-stop finish
    user_guidance = None
    if finish_reason and finish_reason != "stop":
        trunc = _analyze_truncation(raw_content or "")
        advice = _advice_for_finish_reason(
            finish_reason=finish_reason,
            usage=usage,
            advanced_options=None,  # not available at this layer
            has_reasoning=bool(reasoning),
        )
        additional["truncation_analysis"] = trunc
        additional["tuning_advice"] = advice
        user_guidance = _build_user_guidance(
            finish_reason=finish_reason,
            truncation=trunc,
            advice=advice,
        )
        additional["user_guidance"] = user_guidance

    # Handle completely empty content early (common when tokens were consumed by reasoning)
    if raw_content is None or (isinstance(raw_content, str) and raw_content.strip() == ""):
        additional["json_error"] = "empty_content"
        additional["raw_response"] = raw_content
        if "truncation_analysis" not in additional:
            additional["truncation_analysis"] = _analyze_truncation(raw_content or "")
        if user_guidance is None and (finish_reason and finish_reason != "stop"):
            additional["user_guidance"] = _build_user_guidance(
                finish_reason=finish_reason,
                truncation=additional["truncation_analysis"],
                advice=additional.get("tuning_advice"),
            )

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

        friendly = (additional.get("user_guidance") or {}).get("user_message") or \
                   "The model produced no JSON output; try increasing max_completion_tokens and lowering reasoning_effort."
        technical = (
            f"Non-stop finish ('{finish_reason}'): empty content. "
            f"The model likely exhausted tokens during reasoning before emitting JSON."
        )
        raise IncompleteLLMResponseError(technical, friendly)

    # Parse JSON robustly
    try:
        result_json = safe_json_loads(raw_content)
    except Exception as e:
        # Record the failure but don't crash the whole trial; persist raw for later inspection
        additional["json_error"] = str(e)
        additional["raw_response"] = raw_content
        if "truncation_analysis" not in additional:
            additional["truncation_analysis"] = _analyze_truncation(raw_content or "")

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

        # If model finished due to non-stop reason, raise a clearer, user-friendly error
        if finish_reason and finish_reason != "stop":
            tail = additional.get("truncation_analysis", {}).get("tail_snippet", "")
            technical = (
                f"Non-stop finish ('{finish_reason}'): response likely incomplete. "
                f"JSON parse failed: {e}. Tail: {tail!r}"
            )
            friendly = (user_guidance or {}).get("user_message") or \
                "The model stopped early; try increasing max_completion_tokens and lowering reasoning_effort."
            raise IncompleteLLMResponseError(technical, friendly)
        # Otherwise surface the parse failure as before
        raise

    # If we got here, parsing succeeded; collect additional metadata
    if finish_reason and finish_reason != "stop":
        additional["warning"] = (
            f"Model finished with '{finish_reason}'. Output parsed but may be incomplete or filtered."
        )

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
