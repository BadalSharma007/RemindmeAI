from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db
from app.models.user import User
from app.schemas.preference import PreferencePatch, PreferenceRead

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=PreferenceRead)
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> PreferenceRead:
    """Return the current user's preferences."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return PreferenceRead(
        timezone=user.timezone,
        reminder_lead_minutes=user.reminder_lead_minutes,
        channels=["email"],  # Phase 1: email only
    )


@router.put("", response_model=PreferenceRead)
async def update_preferences(
    patch: PreferencePatch,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> PreferenceRead:
    """Update user preferences."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = patch.model_dump(exclude_unset=True)
    if "timezone" in update_data:
        user.timezone = update_data["timezone"]
    if "reminder_lead_minutes" in update_data:
        user.reminder_lead_minutes = update_data["reminder_lead_minutes"]

    await db.commit()
    await db.refresh(user)
    return PreferenceRead(
        timezone=user.timezone,
        reminder_lead_minutes=user.reminder_lead_minutes,
        channels=["email"],
    )
