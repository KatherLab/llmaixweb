# backend/src/schemas/other.py
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, field_validator


class UTCModel(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def make_naive_fields_aware(cls, value: Any) -> Any:
        # Only process datetime instances that are naive
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            # Optional: normalize to UTC if already tz-aware but not UTC
            # return value.astimezone(timezone.utc)
        return value


# ── LLM connection-test request bodies ──────────────────────────────────────
# These fields used to be query parameters, which leaked api_key / base_url
# into URLs and access logs. They now travel in a POST body instead.
class LLMConnectionRequest(BaseModel):
    api_key: str | None = None
    base_url: str | None = None


class LLMModelTestRequest(LLMConnectionRequest):
    llm_model: str | None = None


class LLMModelSchemaTestRequest(LLMModelTestRequest):
    project_id: int
    schema_id: int | None = None
    max_completion_tokens: int | None = None
    temperature: float | None = None
    reasoning_effort: str | None = None  # "low" | "medium" | "high"


class LLMVlmImageSupportRequest(LLMModelTestRequest):
    pass
