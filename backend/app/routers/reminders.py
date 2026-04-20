from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db
from app.models.reminder import Reminder
from app.schemas.reminder import ReminderRead, SnoozeRequest

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderRead])
async def list_reminders(
    status: str | None = Query(None, description="Filter by status: pending, sent, failed, snoozed"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> list[ReminderRead]:
    """List reminders for the authenticated user."""
    stmt = select(Reminder).where(Reminder.user_id == uuid.UUID(current_user_id))
    if status:
        stmt = stmt.where(Reminder.status == status)
    stmt = stmt.order_by(Reminder.scheduled_at.asc()).limit(limit)

    result = await db.execute(stmt)
    reminders = result.scalars().all()
    return [ReminderRead.model_validate(r) for r in reminders]


@router.post("/{reminder_id}/snooze", response_model=ReminderRead)
async def snooze_reminder(
    reminder_id: uuid.UUID,
    body: SnoozeRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> ReminderRead:
    """Snooze a reminder until a future datetime."""
    result = await db.execute(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.user_id == uuid.UUID(current_user_id),
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    reminder.snooze_until = body.snooze_until
    reminder.scheduled_at = body.snooze_until
    reminder.status = "snoozed"

    # Update Redis sorted set
    try:
        import redis as redis_lib
        from app.config import settings
        from app.services.reminders.scheduler import ReminderScheduler

        r = redis_lib.from_url(settings.redis_url)
        scheduler = ReminderScheduler(r)
        scheduler.snooze(reminder_id, body.snooze_until)
    except Exception:
        pass

    await db.commit()
    await db.refresh(reminder)
    return ReminderRead.model_validate(reminder)
