"""Rescue task — re-queues emails that were saved but never NLP-processed.

Runs every 5 minutes via Celery Beat. Finds ExtractedEmail rows that are:
- is_processed=False (never completed)
- is_spam=False (not already filtered)
- created_at > 2 minutes ago (gives the normal pipeline time to run first)

These are "orphaned" emails where publish_email_for_nlp failed or the
worker crashed before marking is_processed=True. Re-queuing them ensures
no email is permanently lost.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def _run(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _register_rescue_task():
    from app.core.celery_app import celery_app

    @celery_app.task(
        name="app.services.nlp.rescue.rescue_orphaned_emails",
        bind=True,
        max_retries=2,
    )
    def rescue_orphaned_emails(self) -> dict:
        """Find and re-queue orphaned emails."""
        try:
            return _run(_rescue_async())
        except Exception as exc:
            logger.error("Rescue task failed: %s", exc, exc_info=True)
            raise self.retry(exc=exc, countdown=60)

    return rescue_orphaned_emails


async def _rescue_async() -> dict:
    from sqlalchemy import select
    from app.database import make_session_factory
    from app.models.extracted_email import ExtractedEmail
    from app.services.events.bus import publish_email_for_nlp

    AsyncSessionLocal = make_session_factory()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=2)
    rescued = 0

    async with AsyncSessionLocal() as db:
        stmt = (
            select(ExtractedEmail)
            .where(
                ExtractedEmail.is_processed == False,
                ExtractedEmail.is_spam == False,
                ExtractedEmail.created_at < cutoff,
            )
            .limit(50)
        )
        result = await db.execute(stmt)
        orphans = result.scalars().all()

        for email in orphans:
            try:
                publish_email_for_nlp(email.id)
                rescued += 1
                logger.info("Rescued orphaned email %s (%s)", email.id, email.subject)
            except Exception as exc:
                logger.error("Failed to rescue email %s: %s", email.id, exc)

    if rescued:
        logger.warning("Rescue task re-queued %d orphaned emails", rescued)
    return {"rescued": rescued}


rescue_orphaned_emails = _register_rescue_task()
