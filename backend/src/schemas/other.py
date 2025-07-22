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
