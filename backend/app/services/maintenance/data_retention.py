"""GDPR data-retention automation — nightly purge Celery task.

Deletes old personal data according to configurable retention windows:

  extracted_emails  — processed rows older than ``EMAIL_RETENTION_DAYS``   (default 90)
  deadlines         — completed/dismissed rows older than ``DEADLINE_RETENTION_DAYS`` (default 365)
  reminders         — sent/failed rows older than ``REMINDER_RETENTION_DAYS`` (default 365)

Rows still in ``pending`` status are never purged automatically (they may
still be actionable).

Schedule: Celery Beat — once per day at 02:00 UTC (added to ``celery_app.py``).

Audit: Each run logs a deletion summary with counts per table for compliance.
The summary is also returned from the task for optional storage in a monitoring
system.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

# Default retention windows (days) — override via config
EMAIL_RETENTION_DAYS = 90
DEADLINE_RETENTION_DAYS = 365
REMINDER_RETENTION_DAYS = 365


@celery_app.task(name="app.services.maintenance.data_retention.purge_old_data")
def purge_old_data() -> dict:
    """Celery task: purge personal data beyond retention windows.

    Returns
    -------
    dict with keys:
        ``run_at``          — ISO timestamp of this run
        ``emails_deleted``  — count of ``ExtractedEmail`` rows removed
        ``deadlines_deleted``— count of ``Deadline`` rows removed
        ``reminders_deleted``— count of ``Reminder`` rows removed
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_purge_async())
    finally:
        loop.close()


async def _purge_async() -> dict:
    from sqlalchemy import delete, func, select
    from app.database import make_session_factory
    AsyncSessionLocal = make_session_factory()
    from app.models.extracted_email import ExtractedEmail
    from app.models.deadline import Deadline
    from app.models.reminder import Reminder

    now = datetime.now(timezone.utc)
    results = {
        "run_at": now.isoformat(),
        "emails_deleted": 0,
        "deadlines_deleted": 0,
        "reminders_deleted": 0,
    }

    async with AsyncSessionLocal() as db:
        # --- ExtractedEmail: processed rows older than EMAIL_RETENTION_DAYS ---
        email_cutoff = now - timedelta(days=EMAIL_RETENTION_DAYS)
        stmt = (
            delete(ExtractedEmail)
            .where(
                ExtractedEmail.is_processed == True,
                ExtractedEmail.created_at < email_cutoff,
            )
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(stmt)
        results["emails_deleted"] = result.rowcount

        # --- Deadline: completed/dismissed rows older than DEADLINE_RETENTION_DAYS ---
        deadline_cutoff = now - timedelta(days=DEADLINE_RETENTION_DAYS)
        stmt = (
            delete(Deadline)
            .where(
                Deadline.status.in_(["completed", "dismissed"]),
                Deadline.created_at < deadline_cutoff,
            )
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(stmt)
        results["deadlines_deleted"] = result.rowcount

        # --- Reminder: sent/failed rows older than REMINDER_RETENTION_DAYS ---
        reminder_cutoff = now - timedelta(days=REMINDER_RETENTION_DAYS)
        stmt = (
            delete(Reminder)
            .where(
                Reminder.status.in_(["sent", "failed"]),
                Reminder.created_at < reminder_cutoff,
            )
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(stmt)
        results["reminders_deleted"] = result.rowcount

        await db.commit()

    logger.info(
        "Data retention purge complete: emails=%d deadlines=%d reminders=%d",
        results["emails_deleted"],
        results["deadlines_deleted"],
        results["reminders_deleted"],
    )
    return results
