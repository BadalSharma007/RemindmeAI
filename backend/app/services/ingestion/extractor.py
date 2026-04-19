from __future__ import annotations

import base64
import email.utils
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class EmailMetadata:
    """Only the minimal fields we extract from a raw Gmail API message.
    The full email body is NEVER stored."""

    message_id: str
    subject: str
    sender: str
    received_at: datetime
    snippet: str  # max 500 chars


def extract_email_metadata(raw_message: dict) -> EmailMetadata:
    """
    Parse a Gmail API message dict into EmailMetadata.
    Extracts ONLY: subject, from, date, snippet.
    Never persists the decoded body.
    """
    headers = {
        h["name"].lower(): h["value"]
        for h in raw_message.get("payload", {}).get("headers", [])
    }

    subject = headers.get("subject", "(no subject)")[:500]
    sender = headers.get("from", "")[:255]

    # Parse date from header or use internalDate (ms since epoch)
    date_str = headers.get("date", "")
    if date_str:
        try:
            parsed_tuple = email.utils.parsedate_tz(date_str)
            if parsed_tuple:
                ts = email.utils.mktime_tz(parsed_tuple)
                received_at = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                received_at = _from_internal_date(raw_message)
        except Exception:
            received_at = _from_internal_date(raw_message)
    else:
        received_at = _from_internal_date(raw_message)

    # Use Gmail's own snippet (already ≤500 chars) — no body decoding needed
    snippet = raw_message.get("snippet", "")[:500]

    return EmailMetadata(
        message_id=raw_message["id"],
        subject=subject,
        sender=sender,
        received_at=received_at,
        snippet=snippet,
    )


def _from_internal_date(raw_message: dict) -> datetime:
    """Convert Gmail's internalDate (ms since epoch) to UTC datetime."""
    internal_ms = int(raw_message.get("internalDate", 0))
    return datetime.fromtimestamp(internal_ms / 1000, tz=timezone.utc)
