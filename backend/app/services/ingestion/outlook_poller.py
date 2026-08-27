"""Outlook email poller — Microsoft Graph API, parallel per-connection.

Same architecture as gmail_poller: Beat fires `poll_all_outlook_connections`
every 60 s, which dispatches one `poll_single_outlook_connection` subtask per
active connection so all accounts are polled in parallel.

Delta / incremental sync uses `@odata.deltaLink` stored in `history_id`.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

import httpx

from app.core.celery_app import celery_app
from app.core.security import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

_GRAPH_MESSAGES_URL = "https://graph.microsoft.com/v1.0/me/messages"
_GRAPH_DELTA_URL = "https://graph.microsoft.com/v1.0/me/messages/delta"
_SELECT_FIELDS = "id,subject,from,receivedDateTime,bodyPreview,internetMessageHeaders"


# ---------------------------------------------------------------------------
# Beat entry-point
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.services.ingestion.outlook_poller.poll_all_outlook_connections",
    bind=True,
    max_retries=2,
)
def poll_all_outlook_connections(self) -> dict:
    """Celery Beat task (every 1 min). Dispatches one subtask per connection."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_dispatch_all_connections())
    except Exception as exc:
        logger.error("Outlook dispatch task failed: %s", exc, exc_info=True)
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
                EmailConnection.provider == "outlook",
            )
        )
        connection_ids = [str(row[0]) for row in result.all()]

    for conn_id in connection_ids:
        poll_single_outlook_connection.delay(conn_id)
        dispatched += 1

    logger.info("Dispatched %d Outlook poll subtasks", dispatched)
    return {"dispatched": dispatched}


# ---------------------------------------------------------------------------
# Per-connection subtask
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.services.ingestion.outlook_poller.poll_single_outlook_connection",
    bind=True,
    max_retries=3,
    queue="polling",
)
def poll_single_outlook_connection(self, connection_id: str) -> dict:
    """Poll one Outlook connection independently. Retries on failure."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_poll_connection_async(connection_id))
    except Exception as exc:
        logger.error(
            "Outlook poll failed for connection %s: %s", connection_id, exc, exc_info=True
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
    """Poll Microsoft Graph for new messages. Returns count of new emails saved."""
    from sqlalchemy import select
    from app.models.extracted_email import ExtractedEmail
    from app.services.events.bus import publish_email_for_nlp

    access_token = await _ensure_fresh_token(db, connection)

    url = connection.history_id or _GRAPH_DELTA_URL
    params = {
        "$select": _SELECT_FIELDS,
        "$top": 20,
        "$filter": "isRead eq false",
        "$orderby": "receivedDateTime desc",
    }

    resp = await client.get(
        url if "delta" in url else _GRAPH_MESSAGES_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        params=params if not connection.history_id else {},
    )
    resp.raise_for_status()
    data = resp.json()

    messages = data.get("value", [])

    next_delta = data.get("@odata.deltaLink")
    if next_delta:
        connection.history_id = next_delta

    count = 0
    for msg in messages:
        message_id = msg.get("id", "")
        if not message_id:
            continue

        existing = await db.execute(
            select(ExtractedEmail).where(
                ExtractedEmail.connection_id == connection.id,
                ExtractedEmail.message_id == message_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        subject = msg.get("subject") or ""
        snippet = (msg.get("bodyPreview") or "")[:500]
        sender_obj = msg.get("from", {}).get("emailAddress", {})
        sender = sender_obj.get("address") or sender_obj.get("name") or ""

        received_str = msg.get("receivedDateTime", "")
        try:
            received_at = datetime.fromisoformat(received_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            received_at = datetime.now(timezone.utc)

        headers: dict[str, str] = {}
        for hdr in msg.get("internetMessageHeaders", []):
            headers[hdr.get("name", "").lower()] = hdr.get("value", "")

        email_row = ExtractedEmail(
            connection_id=connection.id,
            message_id=message_id,
            subject=subject,
            sender=sender,
            received_at=received_at,
            snippet=snippet,
            is_processed=False,
        )
        db.add(email_row)
        await db.flush()

        publish_email_for_nlp(email_row.id)
        count += 1

    connection.last_polled_at = datetime.now(timezone.utc)
    await db.commit()
    return count


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

async def _ensure_fresh_token(db, connection) -> str:
    """Decrypt and refresh the Outlook access token under a Redis lock if near expiry."""
    from datetime import timedelta
    from app.services.oauth.outlook import outlook_oauth_client
    import redis as _redis
    from app.config import settings as _cfg

    if outlook_oauth_client is None:
        raise RuntimeError("Outlook OAuth client is not configured.")

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

            tokens = await outlook_oauth_client.refresh_access_token(refresh_token)
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
