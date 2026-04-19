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
            raise self.retry(exc=exc)

    return process_email_nlp


# Register when the module is imported
process_email_nlp = _register_task()


# ---------------------------------------------------------------------------
# Async implementation
# ---------------------------------------------------------------------------

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
    from app.services.nlp.cleaner import clean_text
    from app.services.nlp.classifier import classify_email_combined
    from app.services.nlp.deadline_extractor import extract_deadlines

    result = {
        "email_id": email_id,
        "is_spam": False,
        "deadlines_created": 0,
        "reminders_created": 0,
    }

    async with AsyncSessionLocal() as db:
        # Load email
        stmt = select(ExtractedEmail).where(ExtractedEmail.id == email_id)
        row = await db.execute(stmt)
        email = row.scalar_one_or_none()
        if email is None:
            logger.warning("process_email_nlp: email %s not found", email_id)
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

        # 3. Deadline extraction — LangGraph agent (Gemma) with spaCy fallback
        from app.config import settings as cfg
        if cfg.enable_langgraph:
            try:
                from app.services.langgraph.deadline_agent import extract_deadlines_with_agent
                agent_results = extract_deadlines_with_agent(
                    subject=email.subject or "",
                    snippet=email.snippet or "",
                    received_at=email.received_at or datetime.now(timezone.utc),
                )
                # Convert to same format as spaCy extractor
                class _DL:
                    def __init__(self, d):
                        self.due_at = d['due_at']
                        self.confidence = d['confidence']
                        self.source_text = d['source_text']
                raw_deadlines = [_DL(d) for d in agent_results]
                logger.info("LangGraph extracted %d deadlines for email %s", len(raw_deadlines), email_id)
            except Exception as lg_exc:
                logger.warning("LangGraph failed, falling back to spaCy: %s", lg_exc)
                text_for_nlp = clean_text(f"{email.subject} {email.snippet}")
                raw_deadlines = extract_deadlines(
                    text_for_nlp,
                    reference_time=email.received_at or datetime.now(timezone.utc),
                )
        else:
            text_for_nlp = clean_text(f"{email.subject} {email.snippet}")
            raw_deadlines = extract_deadlines(
                text_for_nlp,
                reference_time=email.received_at or datetime.now(timezone.utc),
            )

        # Load Gmail access token for Calendar (best-effort)
        access_token: str | None = None
        try:
            from app.core.security import decrypt_token
            access_token = decrypt_token(connection.access_token_enc)
        except Exception:
            pass

        for dl in raw_deadlines:
            # 4. Create Deadline row
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

            # 6. Schedule reminder
            fire_at = dl.due_at - timedelta(minutes=user.reminder_lead_minutes)
            now = datetime.now(timezone.utc)
            if fire_at > now:
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

        email.is_processed = True
        await db.commit()

    return result
