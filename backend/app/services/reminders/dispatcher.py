from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.services.reminders.dispatcher.dispatch_due_reminders")
def dispatch_due_reminders() -> dict:
    """
    Celery Beat task (every 30s).
    Pulls due reminders from Redis sorted set, dispatches to notification channels,
    and marks them as sent in both Redis and PostgreSQL.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_dispatch_async())
    finally:
        loop.close()


async def _dispatch_async() -> dict:
    import redis as redis_lib
    from sqlalchemy import select
    from app.config import settings
    from app.database import make_session_factory
    AsyncSessionLocal = make_session_factory()
    from app.models.reminder import Reminder
    from app.models.deadline import Deadline
    from app.models.user import User
    from app.services.reminders.scheduler import ReminderScheduler
    from app.services.notifications.email_sender import SESEmailSender

    r = redis_lib.from_url(settings.redis_url)
    scheduler = ReminderScheduler(r)
    now = datetime.now(timezone.utc)

    due_ids = scheduler.get_due(now=now, batch_size=100)
    if not due_ids:
        return {"dispatched": 0, "failed": 0}

    dispatched = 0
    failed = 0
    processed_ids: list[str] = []

    async with AsyncSessionLocal() as db:
        for rid in due_ids:
            try:
                # Load reminder with deadline and user
                stmt = (
                    select(Reminder)
                    .where(Reminder.id == rid)
                    .where(Reminder.status == "pending")
                )
                result = await db.execute(stmt)
                reminder = result.scalar_one_or_none()

                if not reminder:
                    # Already processed or not found — remove from sorted set
                    processed_ids.append(rid)
                    continue

                # Load deadline
                dl_result = await db.execute(
                    select(Deadline).where(Deadline.id == reminder.deadline_id)
                )
                deadline = dl_result.scalar_one_or_none()

                # Load user
                user_result = await db.execute(
                    select(User).where(User.id == reminder.user_id)
                )
                user = user_result.scalar_one_or_none()

                if not deadline or not user:
                    reminder.status = "failed"
                    reminder.last_error = "Deadline or user not found"
                    processed_ids.append(rid)
                    continue

                # Dispatch to channel
                success = await _send_reminder(reminder, deadline, user)

                if success:
                    reminder.status = "sent"
                    reminder.sent_at = datetime.now(timezone.utc)
                    dispatched += 1
                else:
                    reminder.status = "failed"
                    failed += 1

                processed_ids.append(rid)

            except Exception as exc:
                logger.error("Error dispatching reminder %s: %s", rid, exc, exc_info=True)
                failed += 1
                processed_ids.append(rid)

        await db.commit()

    # Remove from Redis sorted set
    scheduler.mark_processed(processed_ids)

    logger.info("Dispatcher: dispatched=%d failed=%d", dispatched, failed)
    return {"dispatched": dispatched, "failed": failed}


async def _send_reminder(reminder, deadline, user) -> bool:
    """
    Route to the appropriate notification channel. Returns True on success.

    Phase 2 channels:
      email — AWS SES (Phase 1)
      push  — Firebase Cloud Messaging (Phase 2)
    """
    try:
        if reminder.channel == "email":
            from app.services.notifications.email_sender import SESEmailSender  # noqa: PLC0415

            await SESEmailSender().send_reminder_email(
                to_address=user.email,
                deadline_title=deadline.title,
                due_at=deadline.due_at,
                reminder_id=str(reminder.id),
            )
            return True

        elif reminder.channel == "push":
            if not user.fcm_token:
                logger.warning(
                    "Cannot push: user %s has no FCM token registered.", user.id
                )
                reminder.last_error = "No FCM token registered for user"
                return False

            from app.services.notifications.push_sender import FCMSender  # noqa: PLC0415

            await FCMSender().send_push_notification(
                fcm_token=user.fcm_token,
                deadline_title=deadline.title,
                due_at=deadline.due_at,
                reminder_id=str(reminder.id),
            )
            return True

        else:
            logger.warning("Channel '%s' not implemented.", reminder.channel)
            return False

    except Exception as exc:
        reminder.last_error = str(exc)[:500]
        logger.error("Failed to send reminder %s: %s", reminder.id, exc)
        return False
