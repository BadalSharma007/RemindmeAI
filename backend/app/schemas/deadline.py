from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator


class DeadlineRead(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    due_at: datetime
    confidence_score: float
    source_text: str | None = None
    status: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}

    @field_validator("due_at")
    @classmethod
    def must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("due_at must be timezone-aware (UTC)")
        return v


class DeadlinePatch(BaseModel):
    status: Literal["pending", "reminded", "dismissed", "completed"] | None = None
    title: str | None = None

    model_config = {"extra": "forbid"}
