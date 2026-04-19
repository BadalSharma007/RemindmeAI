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


@celery_app.task(name="app.services.ingestion.gmail_poller.poll_all_gmail_connections")
def poll_all_gmail_connections() -> dict:
    """
    Celery Beat task (every 5 min).
    Fetches all active Gmail connections and polls each for new messages.
    Returns a summary of results.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_poll_all_async())
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
            EmailConnection.provider == "gmail",
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
                    "Error polling connection %s: %s", conn.id, exc, exc_info=True
                )
                results["errors"] += 1

    return results


async def _poll_single_connection(db, connection) -> int:
    """Poll Gmail for new messages. Saves emails and publishes to NLP event bus."""
    from sqlalchemy import select
    from app.models.extracted_email import ExtractedEmail
    from app.services.ingestion.extractor import extract_email_metadata
    from app.services.events.bus import publish_email_for_nlp
    from app.services.resilience.circuit_breaker import CircuitBreakerOpen

    access_token = await _ensure_fresh_token(db, connection)

    # Fetch messages received since last poll (read or unread)
    after_ts = connection.last_polled_at or (datetime.now(timezone.utc) - timedelta(days=7))
    after_epoch = int(after_ts.timestamp())
    query = f"after:{after_epoch}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                GMAIL_MESSAGES_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"maxResults": 50, "q": query},
            )
            resp.raise_for_status()
            messages = resp.json().get("messages", [])
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (401, 403):
            logger.warning("Gmail auth error for connection %s: %s", connection.id, exc)
            connection.is_active = False
            await db.commit()
            return 0
        raise

    count = 0
    for msg_ref in messages:
        message_id = msg_ref["id"]

        # Dedup check
        existing = await db.execute(
            select(ExtractedEmail).where(
                ExtractedEmail.connection_id == connection.id,
                ExtractedEmail.message_id == message_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        # Fetch full message metadata
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                GMAIL_MESSAGE_URL.format(id=message_id),
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date", "List-Unsubscribe", "Precedence"]},
            )
            if resp.status_code != 200:
                continue
            raw = resp.json()

        metadata = extract_email_metadata(raw)

        # Save extracted email (never full body)
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
        await db.flush()  # get email_row.id

        # Phase 3: publish to NLP queue (decoupled)
        try:
            publish_email_for_nlp(email_row.id)
        except Exception as exc:
            logger.warning("Failed to publish email %s to NLP queue: %s", email_row.id, exc)

        count += 1

    # Update last_polled_at
    connection.last_polled_at = datetime.now(timezone.utc)
    await db.commit()
    return count


async def _ensure_fresh_token(db, connection) -> str:
    """
    Decrypt the stored access token. If it expires within 5 minutes,
    refresh it and re-encrypt+save. Returns the plaintext access token.
    This is the ONLY place in the codebase that handles plaintext OAuth tokens.
    """
    from app.services.oauth.gmail import gmail_oauth_client

    access_token = decrypt_token(connection.access_token_enc)
    refresh_token = decrypt_token(connection.refresh_token_enc)

    now = datetime.now(timezone.utc)
    expires_soon = (
        connection.token_expiry is None
        or connection.token_expiry <= now + timedelta(minutes=5)
    )

    if expires_soon:
        tokens = await gmail_oauth_client.refresh_access_token(refresh_token)
        connection.access_token_enc = encrypt_token(tokens.access_token)
        connection.token_expiry = tokens.expires_at
        if tokens.refresh_token:
            connection.refresh_token_enc = encrypt_token(tokens.refresh_token)
        await db.commit()
        access_token = tokens.access_token

    return access_token
