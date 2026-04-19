"""Phase 2 — Notifications router.

Endpoints:
  POST   /notifications/register-device    Register FCM token for push notifications
  DELETE /notifications/unregister-device  Remove stored FCM token
  POST   /deadlines/{deadline_id}/feedback Submit user feedback on a detected deadline
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db
from app.models.deadline import Deadline
from app.models.user import User

router = APIRouter(tags=["notifications"])


# ---------------------------------------------------------------------------
# Schemas (defined inline — lightweight, no separate schema file needed)
# ---------------------------------------------------------------------------

class DeviceRegistration(BaseModel):
    fcm_token: str


class FeedbackRequest(BaseModel):
    helpful: bool
    """True = deadline was correctly identified; False = false positive."""


# ---------------------------------------------------------------------------
# FCM device token management
# ---------------------------------------------------------------------------

@router.post(
    "/notifications/register-device",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def register_device(
    body: DeviceRegistration,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    """
    Store the FCM registration token for the authenticated user's device.
    Overwrites any existing token (one token per user in Phase 2).
    """
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(current_user_id))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.fcm_token = body.fcm_token
    await db.commit()


@router.delete(
    "/notifications/unregister-device",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def unregister_device(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    """Remove the stored FCM token, disabling push notifications for this user."""
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(current_user_id))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.fcm_token = None
    await db.commit()


# ---------------------------------------------------------------------------
# User feedback loop — deadline accuracy
# ---------------------------------------------------------------------------

@router.post(
    "/deadlines/{deadline_id}/feedback",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def submit_deadline_feedback(
    deadline_id: uuid.UUID,
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    """
    Record whether the user considers a deadline detection correct.

    ``helpful=True``  → confirmed correct (used to boost future confidence)
    ``helpful=False`` → false positive (used to improve classifier training data)

    The ``user_confirmed`` field is stored on the Deadline row and can be
    exported to fine-tune the Phase 3 ML classifier.
    """
    result = await db.execute(
        select(Deadline).where(
            Deadline.id == deadline_id,
            Deadline.user_id == uuid.UUID(current_user_id),
        )
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    deadline.user_confirmed = body.helpful
    await db.commit()
