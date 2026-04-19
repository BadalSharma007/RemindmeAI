from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db
from app.models.unsubscribe_action import UnsubscribeAction

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("")
async def list_subscriptions(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    """List detected promotional senders with unsubscribe options."""
    result = await db.execute(
        select(UnsubscribeAction).where(
            UnsubscribeAction.user_id == uuid.UUID(current_user_id)
        )
    )
    actions = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "sender_email": a.sender_email,
            "sender_pattern": a.sender_pattern,
            "status": a.status,
            "unsubscribe_url": a.unsubscribe_url,
        }
        for a in actions
    ]


@router.post("/{subscription_id}/unsubscribe")
async def unsubscribe(
    subscription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Execute unsubscribe for a promotional sender.
    Always requires explicit user action — never auto-unsubscribes.
    """
    result = await db.execute(
        select(UnsubscribeAction).where(
            UnsubscribeAction.id == subscription_id,
            UnsubscribeAction.user_id == uuid.UUID(current_user_id),
        )
    )
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if action.status == "executed":
        return {"status": "already_executed", "id": str(action.id)}

    # Execute unsubscribe (Phase 3: will follow List-Unsubscribe URL)
    action.status = "executed"
    await db.commit()

    return {"status": "executed", "id": str(action.id)}
