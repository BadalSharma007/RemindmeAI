"""Gmail poller — parallel per-connection polling.

Celery Beat fires `poll_all_gmail_connections` every 60 s. That task
immediately dispatches one `poll_single_gmail_connection` subtask per active
connection so every account is polled **in parallel** — a slow or failing
connection cannot block any other.

Filter strategy
---------------
- No `is:important`: Gmail can take several minutes to label a new email as
  important, so fresh emails frequently miss that filter.
- Category exclusions: `-category:promotions -category:social -category:forums`
  eliminate newsletters / social pings before NLP runs.
- 120-second overlap: subtract 120 s from `last_polled_at` to cover emails
  that arrived inside the previous poll window but whose index timestamp
  trailed the poll start.
- Downstream spam filter still runs as a safety net.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.core.celery_app import celery_app
from app.core.security import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
GMAIL_MESSAGE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/{id}"


# ---------------------------------------------------------------------------
# Beat entry-point — dispatches subtasks, returns immediately
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.services.ingestion.gmail_poller.poll_all_gmail_connections",
    bind=True,
    max_retries=2,
)
def poll_all_gmail_connections(self) -> dict:
    """Celery Beat task (every 1 min). Dispatches one subtask per connection."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_dispatch_all_connections())
    except Exception as exc:
        logger.error("Gmail dispatch task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    finally:
        loop.close()


async def _dispatch_all_connections() -> dict:
    from sqlalchemy import select
    from app.database import make_session_factory
    from app.models.email_connection import EmailConnection

    AsyncSessionLocal = make_session_factory()
    dispatched = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(EmailConnection.id).where(
                EmailConnection.is_active == True,
                EmailConnection.provider == "gmail",
            )
        )
        connection_ids = [str(row[0]) for row in result.all()]

    for conn_id in connection_ids:
        poll_single_gmail_connection.delay(conn_id)
        dispatched += 1

    logger.info("Dispatched %d Gmail poll subtasks", dispatched)
    return {"dispatched": dispatched}


# ---------------------------------------------------------------------------
# Per-connection subtask — runs in parallel with all others
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.services.ingestion.gmail_poller.poll_single_gmail_connection",
    bind=True,
    max_retries=3,
    queue="polling",
)
def poll_single_gmail_connection(self, connection_id: str) -> dict:
    """Poll one Gmail connection independently. Retries on failure."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_poll_connection_async(connection_id))
    except Exception as exc:
        logger.error(
            "Gmail poll failed for connection %s: %s", connection_id, exc, exc_info=True
        )
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        loop.close()


async def _poll_connection_async(connection_id: str) -> dict:
    from sqlalchemy import select
    from app.database import make_session_factory
    from app.models.email_connection import EmailConnection

    AsyncSessionLocal = make_session_factory()

    async with httpx.AsyncClient(timeout=30) as client:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(EmailConnection).where(EmailConnection.id == connection_id)
            )
            connection = result.scalar_one_or_none()
            if not connection or not connection.is_active:
                return {"connection_id": connection_id, "processed": 0, "skipped": True}

            count = await _poll_single_connection(db, connection, client)
            return {"connection_id": connection_id, "processed": count}


# ---------------------------------------------------------------------------
# Core polling logic
# ---------------------------------------------------------------------------

async def _poll_single_connection(db, connection, client: httpx.AsyncClient) -> int:
    """Poll Gmail API for new messages, save, and publish to NLP queue."""
    from sqlalchemy import select
    from app.models.extracted_email import ExtractedEmail
    from app.services.ingestion.extractor import extract_email_metadata
    from app.services.events.bus import publish_email_for_nlp

    access_token = await _ensure_fresh_token(db, connection)

    after_ts = connection.last_polled_at or (datetime.now(timezone.utc) - timedelta(days=7))
    # Subtract 120 s to close the gap between poll windows
    after_epoch = int(after_ts.timestamp()) - 120
    query = (
        f"after:{after_epoch} "
        "-category:promotions -category:social -category:forums -in:spam"
    )

    try:
        resp = await client.get(
            GMAIL_MESSAGES_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"maxResults": 50, "q": query},
        )
        resp.raise_for_status()
        messages = resp.json().get("messages", [])
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (401, 403):
            logger.warning(
                "Gmail auth error for connection %s — refreshing token", connection.id
            )
            try:
                access_token = await _ensure_fresh_token(db, connection)
                resp = await client.get(
                    GMAIL_MESSAGES_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"maxResults": 50, "q": query},
                )
                resp.raise_for_status()
                messages = resp.json().get("messages", [])
            except Exception as refresh_exc:
                logger.error(
                    "Token refresh failed for connection %s: %s", connection.id, refresh_exc
                )
                connection.is_active = False
                await db.commit()
                return 0
        else:
            raise

    count = 0
    for msg_ref in messages:
        message_id = msg_ref["id"]

        existing = await db.execute(
            select(ExtractedEmail).where(
                ExtractedEmail.connection_id == connection.id,
                ExtractedEmail.message_id == message_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        resp = await client.get(
            GMAIL_MESSAGE_URL.format(id=message_id),
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "format": "metadata",
                "metadataHeaders": ["Subject", "From", "Date", "List-Unsubscribe", "Precedence"],
            },
        )
        if resp.status_code != 200:
            continue
        raw = resp.json()

        metadata = extract_email_metadata(raw)

        email_row = ExtractedEmail(
            connection_id=connection.id,
            message_id=metadata.message_id,
            subject=metadata.subject,
            sender=metadata.sender,
            received_at=metadata.received_at,
            snippet=metadata.snippet,
            is_processed=False,
        )
        db.add(email_row)
        await db.flush()

        # Retry publish 3x — rescue task re-queues any still-orphaned emails
        for attempt in range(3):
            try:
                publish_email_for_nlp(email_row.id)
                break
            except Exception:
                if attempt == 2:
                    logger.error(
                        "PUBLISH_FAILED email_id=%s subject=%r — rescue will retry",
                        email_row.id, email_row.subject,
                    )
                else:
                    await asyncio.sleep(1)

        count += 1

    connection.last_polled_at = datetime.now(timezone.utc)
    await db.commit()
    return count


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

async def _ensure_fresh_token(db, connection) -> str:
    """Decrypt access token; refresh under Redis lock if expiring within 5 min."""
    from app.services.oauth.gmail import gmail_oauth_client
    import redis as _redis
    from app.config import settings as _cfg

    access_token = decrypt_token(connection.access_token_enc)
    refresh_token = decrypt_token(connection.refresh_token_enc)

    now = datetime.now(timezone.utc)
    expires_soon = (
        connection.token_expiry is None
        or connection.token_expiry <= now + timedelta(minutes=5)
    )

    if not expires_soon:
        return access_token

    r = _redis.from_url(_cfg.redis_url)
    lock_key = f"token_refresh:{connection.id}"
    lock = r.lock(lock_key, timeout=30, blocking_timeout=25)
    acquired = lock.acquire(blocking=True)
    if acquired:
        try:
            await db.refresh(connection)
            now2 = datetime.now(timezone.utc)
            if (
                connection.token_expiry is not None
                and connection.token_expiry > now2 + timedelta(minutes=5)
            ):
                return decrypt_token(connection.access_token_enc)

            tokens = await gmail_oauth_client.refresh_access_token(refresh_token)
            connection.access_token_enc = encrypt_token(tokens.access_token)
            connection.token_expiry = tokens.expires_at
            if tokens.refresh_token:
                connection.refresh_token_enc = encrypt_token(tokens.refresh_token)
            await db.commit()
            return tokens.access_token
        finally:
            try:
                lock.release()
            except Exception:
                pass
    else:
        await db.refresh(connection)
        return decrypt_token(connection.access_token_enc)
