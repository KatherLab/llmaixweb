# backend/src/schemas/other.py
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


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
    # Bounds mirror what the extraction path forwards to the provider: a
    # negative/absurd value would either be rejected upstream or, worse,
    # accepted and burn cost. temperature 0–2 is the sane LLM range.
    max_completion_tokens: int | None = Field(None, ge=1, le=200_000)
    temperature: float | None = Field(None, ge=0, le=2)
    reasoning_effort: Literal["low", "medium", "high"] | None = None


class LLMVlmImageSupportRequest(LLMModelTestRequest):
    pass
