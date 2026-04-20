from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db
from app.models.deadline import Deadline
from app.models.email_connection import EmailConnection
from app.models.extracted_email import ExtractedEmail
from app.models.reminder import Reminder
from app.schemas.dashboard import DashboardStats

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> DashboardStats:
    """Return aggregate statistics for the user's dashboard."""
    uid = uuid.UUID(current_user_id)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Total deadlines
    total_result = await db.execute(
        select(func.count()).where(Deadline.user_id == uid)
    )
    total_deadlines = total_result.scalar() or 0

    # Pending deadlines
    pending_result = await db.execute(
        select(func.count()).where(Deadline.user_id == uid, Deadline.status == "pending")
    )
    pending_deadlines = pending_result.scalar() or 0

    # Completed deadlines
    completed_result = await db.execute(
        select(func.count()).where(Deadline.user_id == uid, Deadline.status == "completed")
    )
    completed_deadlines = completed_result.scalar() or 0

    # Upcoming reminders (next 24h, pending)
    upcoming_result = await db.execute(
        select(func.count()).where(
            Reminder.user_id == uid,
            Reminder.status == "pending",
            Reminder.scheduled_at <= datetime.now(timezone.utc) + timedelta(hours=24),
        )
    )
    upcoming_reminders = upcoming_result.scalar() or 0

    # Emails processed today
    processed_result = await db.execute(
        select(func.count())
        .select_from(ExtractedEmail)
        .join(EmailConnection, ExtractedEmail.connection_id == EmailConnection.id)
        .where(
            EmailConnection.user_id == uid,
            ExtractedEmail.created_at >= today_start,
        )
    )
    emails_today = processed_result.scalar() or 0

    # Connected accounts
    accounts_result = await db.execute(
        select(func.count()).where(
            EmailConnection.user_id == uid,
            EmailConnection.is_active == True,
        )
    )
    connected_accounts = accounts_result.scalar() or 0

    return DashboardStats(
        total_deadlines=total_deadlines,
        pending_deadlines=pending_deadlines,
        completed_deadlines=completed_deadlines,
        upcoming_reminders=upcoming_reminders,
        emails_processed_today=emails_today,
        connected_accounts=connected_accounts,
    )
