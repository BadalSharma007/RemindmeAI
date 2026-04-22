"""Outlook email poller — Microsoft Graph API.

Celery Beat task (every 5 min) that mirrors the Gmail poller.
After saving new ``ExtractedEmail`` rows it publishes each to the NLP
event bus (``process_email_nlp`` on the ``nlp`` queue) rather than
running NLP inline.

Microsoft Graph Messages API
-----------------------------
  List  : GET https://graph.microsoft.com/v1.0/me/messages
  Single: GET https://graph.microsoft.com/v1.0/me/messages/{id}

Delta / incremental sync uses the ``@odata.deltaLink`` returned by the
first full-sync page response.  The ``delta_link`` is stored on the
``EmailConnection`` row (``history_id`` column — shared with Gmail's
``historyId``).
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

_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=30,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _http_client

_GRAPH_MESSAGES_URL = "https://graph.microsoft.com/v1.0/me/messages"
_GRAPH_DELTA_URL = "https://graph.microsoft.com/v1.0/me/messages/delta"

# Fields to select — we never fetch the full body
_SELECT_FIELDS = "id,subject,from,receivedDateTime,bodyPreview,internetMessageHeaders"


@celery_app.task(
    name="app.services.ingestion.outlook_poller.poll_all_outlook_connections",
    bind=True,
    max_retries=2,
)
def poll_all_outlook_connections(self) -> dict:
    """Celery Beat task (every 1 min). Polls all active Outlook connections."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_poll_all_async())
    except Exception as exc:
        logger.error("Outlook poll task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    finally:
        loop.close()


async def _poll_all_async() -> dict:
    from sqlalchemy import select
    from app.database import make_session_factory
    AsyncSessionLocal = make_session_factory()
    from app.models.email_connection import EmailConnection

    results = {"processed": 0, "errors": 0, "connections": 0}

    async with AsyncSessionLocal() as db:
        stmt = select(EmailConnection).where(
            EmailConnection.is_active == True,
            EmailConnection.provider == "outlook",
        )
        result = await db.execute(stmt)
        connections = result.scalars().all()
        results["connections"] = len(connections)

        for conn in connections:
            try:
                count = await _poll_single_connection(db, conn)
                results["processed"] += count
            except Exception as exc:
                logger.error(
                    "Error polling Outlook connection %s: %s", conn.id, exc, exc_info=True
                )
                results["errors"] += 1

    return results


async def _poll_single_connection(db, connection) -> int:
    """Poll Microsoft Graph for new messages. Returns count of new emails saved."""
    from sqlalchemy import select
    from app.models.extracted_email import ExtractedEmail
    from app.services.events.bus import publish_email_for_nlp

    access_token = await _ensure_fresh_token(db, connection)

    # Use delta link for incremental sync if available, else full sync
    url = connection.history_id or _GRAPH_DELTA_URL
    params = {
        "$select": _SELECT_FIELDS,
        "$top": 20,
        "$filter": "isRead eq false",
        "$orderby": "receivedDateTime desc",
    }

    client = _get_http_client()
    resp = await client.get(
        url if "delta" in url else _GRAPH_MESSAGES_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        params=params if not connection.history_id else {},
    )
    resp.raise_for_status()
    data = resp.json()

    messages = data.get("value", [])

    # Store delta link for next incremental sync
    next_delta = data.get("@odata.deltaLink")
    if next_delta:
        connection.history_id = next_delta

    count = 0
    for msg in messages:
        message_id = msg.get("id", "")
        if not message_id:
            continue

        # Dedup check
        existing = await db.execute(
            select(ExtractedEmail).where(
                ExtractedEmail.connection_id == connection.id,
                ExtractedEmail.message_id == message_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        # Parse metadata
        subject = msg.get("subject") or ""
        snippet = (msg.get("bodyPreview") or "")[:500]
        sender_obj = msg.get("from", {}).get("emailAddress", {})
        sender = sender_obj.get("address") or sender_obj.get("name") or ""

        received_str = msg.get("receivedDateTime", "")
        try:
            received_at = datetime.fromisoformat(received_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            received_at = datetime.now(timezone.utc)

        # Extract internet message headers (spam signals)
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

        # Publish to NLP queue (async, non-blocking)
        publish_email_for_nlp(email_row.id)
        count += 1

    connection.last_polled_at = datetime.now(timezone.utc)
    await db.commit()
    return count


async def _ensure_fresh_token(db, connection) -> str:
    """Decrypt and refresh the Outlook access token if near expiry.
    Uses a Redis distributed lock to prevent concurrent workers from
    both calling Microsoft's token endpoint with the same refresh token.
    """
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
