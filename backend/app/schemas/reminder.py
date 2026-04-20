from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, field_validator


class ReminderRead(BaseModel):
    id: UUID
    deadline_id: UUID
    user_id: UUID
    scheduled_at: datetime
    channel: str
    status: str
    sent_at: datetime | None = None
    snooze_until: datetime | None = None

    model_config = {"from_attributes": True}


class ReminderCreate(BaseModel):
    deadline_id: UUID
    scheduled_at: datetime
    channel: str = "email"

    model_config = {"extra": "forbid"}


class ReminderPatch(BaseModel):
    scheduled_at: datetime | None = None
    channel: str | None = None

    model_config = {"extra": "forbid"}


class SnoozeRequest(BaseModel):
    snooze_until: datetime

    @field_validator("snooze_until")
    @classmethod
    def must_be_future(cls, v: datetime) -> datetime:
        now = datetime.now(timezone.utc)
        # Make naive datetimes UTC-aware for comparison
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= now:
            raise ValueError("snooze_until must be in the future")
        return v
