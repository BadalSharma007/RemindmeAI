"""Decoupled NLP Celery task — consumes from the ``nlp`` queue.

This task is enqueued by ``services/events/bus.py`` after an email is saved
to the database.  It runs the full pipeline:

  1. Load ``ExtractedEmail`` from DB
  2. Spam detection  → skip if spam; record score
  3. Two-tier classification (rule-based + DistilBERT)
  4. Deadline extraction (spaCy NER → dateparser)
  5. For each deadline: create ``Deadline`` row + Google Calendar event
  6. For each deadline: create ``Reminder`` row + schedule in Redis
  7. Mark email ``is_processed=True``

Separating NLP from ingestion means:
  - Ingestion workers scale independently from GPU/CPU-heavy NLP workers.
  - NLP failures do not block email ingestion.
  - The ``nlp`` queue can be routed to a different worker pool.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

logger = logging.getLogger(__name__)


def _run(coro):
    """Run a coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

def _register_task():
    """Late-import registration so the module can be imported without Celery
    being fully configured (important for unit tests)."""
    from app.core.celery_app import celery_app

    @celery_app.task(
        name="app.services.nlp.processor.process_email_nlp",
        bind=True,
        max_retries=3,
        default_retry_delay=60,
        queue="nlp",
        rate_limit="20/m",
    )
    def process_email_nlp(self, email_id: str) -> dict:
        """Process a single ExtractedEmail through the full NLP pipeline.

        Parameters
        ----------
        email_id:
            String representation of the ``ExtractedEmail.id`` UUID.

        Returns
        -------
        dict with keys: email_id, is_spam, deadlines_created, reminders_created
        """
        try:
            return _run(_process_async(email_id))
        except Exception as exc:
            logger.error("NLP processing failed for email %s: %s", email_id, exc, exc_info=True)
            # Exponential backoff: 60s, 120s, 240s
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    return process_email_nlp


# Register when the module is imported
process_email_nlp = _register_task()


# ---------------------------------------------------------------------------
# Async implementation
# ---------------------------------------------------------------------------

def _calibrate_confidence(deadline_dict: dict, subject: str, snippet: str) -> float:
    base = float(deadline_dict.get('confidence', 0.5))
    text = (deadline_dict.get('source_text') or '').lower()
    combined = (subject + ' ' + snippet).lower()
    action_verbs = ['submit', 'due', 'deadline', 'by', 'before', 'last date', 'pay',
                    'register', 'apply', 'attend', 'complete', 'upload', 'report']
    has_action = any(v in text or v in combined for v in action_verbs)
    if has_action and base >= 0.7:
        return min(base * 1.05, 1.0)
    if not has_action and base < 0.8:
        return base * 0.9
    return base


async def _process_async(email_id: str) -> dict:
    from sqlalchemy import select
    from app.database import make_session_factory
    AsyncSessionLocal = make_session_factory()
    from app.models.extracted_email import ExtractedEmail
    from app.models.deadline import Deadline
    from app.models.reminder import Reminder
    from app.models.user import User
    from app.models.email_connection import EmailConnection
    from app.services.nlp.spam_detector import detect_spam
    from app.services.nlp.classifier import classify_email_combined

    result = {
        "email_id": email_id,
        "is_spam": False,
        "deadlines_created": 0,
        "reminders_created": 0,
    }

    async with AsyncSessionLocal() as db:
        # Atomically claim the email — only one worker can process it
        # If another worker already claimed it, scalar_one_or_none() returns None
        claim = await db.execute(
            update(ExtractedEmail)
            .where(ExtractedEmail.id == email_id, ExtractedEmail.is_processed == False)
            .values(is_processed=True)
            .returning(ExtractedEmail)
        )
        email = claim.scalar_one_or_none()
        if email is None:
            logger.debug("process_email_nlp: email %s already claimed or not found", email_id)
            return result

        # Load connection → user
        conn_stmt = select(EmailConnection).where(EmailConnection.id == email.connection_id)
        conn_row = await db.execute(conn_stmt)
        connection = conn_row.scalar_one_or_none()
        if not connection:
            return result

        user_stmt = select(User).where(User.id == connection.user_id)
        user_row = await db.execute(user_stmt)
        user = user_row.scalar_one_or_none()
        if not user:
            return result

        # 1. Spam detection
        spam_result = detect_spam(
            subject=email.subject or "",
            snippet=email.snippet or "",
        )
        email.spam_score = spam_result.spam_score
        email.is_spam = spam_result.is_spam

        if spam_result.is_spam:
            email.is_processed = True
            await db.commit()
            result["is_spam"] = True
            logger.info(
                "Email %s marked as spam (score=%.2f, signals=%s)",
                email_id, spam_result.spam_score, spam_result.signals,
            )
            return result

        # 2. Classification
        classification = classify_email_combined(email.subject or "", email.snippet or "")
        if not classification.is_deadline_related:
            email.is_processed = True
            await db.commit()
            return result

        # 3. Deadline extraction — Gemini via LangGraph (no spaCy fallback)
        # If Gemini fails, un-claim the email so rescue task retries it cleanly
        try:
            from app.services.langgraph.deadline_agent import extract_deadlines_with_agent
            agent_results = extract_deadlines_with_agent(
                subject=email.subject or "",
                snippet=email.snippet or "",
                received_at=email.received_at or datetime.now(timezone.utc),
                user_timezone=user.timezone if user.timezone and user.timezone != "UTC" else "Asia/Kolkata",
            )
            class _DL:
                def __init__(self, d, calibrated_confidence: float):
                    self.due_at = d['due_at']
                    self.confidence = calibrated_confidence
                    self.source_text = d['source_text']

            calibrated = []
            for d in agent_results:
                cal_conf = _calibrate_confidence(d, email.subject or "", email.snippet or "")
                if cal_conf >= 0.6:
                    calibrated.append(_DL(d, cal_conf))
                else:
                    logger.debug("Skipping low-confidence deadline (%.2f): %s", cal_conf, d.get('source_text'))
            raw_deadlines = calibrated
            logger.info("Gemini extracted %d deadlines (after calibration) for email %s", len(raw_deadlines), email_id)
        except Exception as lg_exc:
            logger.error("Gemini extraction failed for email %s: %s — releasing for rescue", email_id, lg_exc)
            # Un-claim so the rescue task can re-queue this email
            await db.execute(
                update(ExtractedEmail)
                .where(ExtractedEmail.id == email_id)
                .values(is_processed=False)
            )
            await db.commit()
            raise

        # Load Gmail access token for Calendar (best-effort)
        access_token: str | None = None
        try:
            from app.core.security import decrypt_token
            access_token = decrypt_token(connection.access_token_enc)
        except Exception:
            pass

        for dl in raw_deadlines:
            now_utc = datetime.now(timezone.utc)
            # Skip deadlines already in the past
            if dl.due_at < now_utc:
                logger.info("Skipping past deadline %s for email %s", dl.due_at, email_id)
                continue
            # Skip suspiciously far-future deadlines (> 2 years)
            if dl.due_at > now_utc + timedelta(days=730):
                logger.warning("Skipping far-future deadline %s for email %s", dl.due_at, email_id)
                continue

            # 4. Create Deadline row — skip if already exists for this email + due_at
            existing_dl = await db.execute(
                select(Deadline).where(
                    Deadline.extracted_email_id == email.id,
                    Deadline.due_at == dl.due_at,
                )
            )
            if existing_dl.scalar_one_or_none():
                continue

            deadline_row = Deadline(
                user_id=user.id,
                extracted_email_id=email.id,
                title=f"Deadline from: {(email.subject or '')[:200]}",
                due_at=dl.due_at,
                confidence_score=dl.confidence,
                source_text=dl.source_text,
                status="pending",
                classifier_tier=classification.tier,
            )
            db.add(deadline_row)
            await db.flush()
            result["deadlines_created"] += 1

            # 5. Google Calendar event (best-effort)
            if access_token:
                try:
                    from app.services.calendar.google_calendar import GoogleCalendarClient
                    cal = GoogleCalendarClient(access_token)
                    event_id = await cal.create_deadline_event(
                        title=deadline_row.title,
                        due_at=dl.due_at,
                        description=dl.source_text or "",
                    )
                    deadline_row.calendar_event_id = event_id
                except Exception as cal_exc:
                    logger.warning("Calendar event creation failed: %s", cal_exc)

            # 6. Schedule reminder — skip if already exists for this deadline
            fire_at = dl.due_at - timedelta(minutes=user.reminder_lead_minutes)
            now = datetime.now(timezone.utc)
            if fire_at > now:
                existing_r = await db.execute(
                    select(Reminder).where(Reminder.deadline_id == deadline_row.id)
                )
                if existing_r.scalar_one_or_none():
                    continue

                reminder_row = Reminder(
                    deadline_id=deadline_row.id,
                    user_id=user.id,
                    scheduled_at=fire_at,
                    channel="email",
                    status="pending",
                )
                db.add(reminder_row)
                await db.flush()
                result["reminders_created"] += 1

                try:
                    from app.services.reminders.scheduler import ReminderScheduler
                    import redis as redis_lib
                    from app.config import settings as cfg
                    r = redis_lib.from_url(cfg.redis_url)
                    scheduler = ReminderScheduler(r)
                    scheduler.schedule(reminder_row.id, fire_at)
                except Exception as redis_exc:
                    logger.warning("Redis scheduling failed: %s", redis_exc)

        await db.commit()

    return result
