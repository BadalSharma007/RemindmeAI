from __future__ import annotations

from pydantic import BaseModel, Field


class PreferenceRead(BaseModel):
    timezone: str = "UTC"
    reminder_lead_minutes: int = 60
    channels: list[str] = Field(default_factory=lambda: ["email"])

    model_config = {"from_attributes": True}


class PreferencePatch(BaseModel):
    timezone: str | None = None
    reminder_lead_minutes: int | None = None
    channels: list[str] | None = None

    model_config = {"extra": "forbid"}
