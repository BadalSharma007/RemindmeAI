from __future__ import annotations

import pytz
from pydantic import BaseModel, Field, field_validator


class PreferenceRead(BaseModel):
    timezone: str = "UTC"
    reminder_lead_minutes: int = 60
    channels: list[str] = Field(default_factory=lambda: ["email"])

    model_config = {"from_attributes": True}


class PreferencePatch(BaseModel):
    timezone: str | None = Field(None, max_length=60)
    reminder_lead_minutes: int | None = Field(None, ge=1, le=1440)
    channels: list[str] | None = None

    model_config = {"extra": "forbid"}

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, v: str | None) -> str | None:
        if v is not None and v not in pytz.all_timezones:
            raise ValueError(f"Unknown timezone: {v!r}. Use a valid IANA timezone name.")
        return v

    @field_validator("channels")
    @classmethod
    def valid_channels(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            allowed = {"email", "push"}
            invalid = [c for c in v if c not in allowed]
            if invalid:
                raise ValueError(f"Invalid channels: {invalid}. Allowed: {sorted(allowed)}")
        return v
