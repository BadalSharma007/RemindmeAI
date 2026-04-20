from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException

router = APIRouter(prefix="/internal", tags=["internal"])

_SECRET = os.environ.get("INTERNAL_POLL_SECRET", "")


@router.post("/trigger-poll")
async def trigger_poll(x_poll_secret: str = Header(...)) -> dict:
    """Called by GitHub Actions cron to trigger Gmail polling."""
    if not _SECRET or x_poll_secret != _SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        from app.services.ingestion.gmail_poller import poll_all_gmail_connections
        poll_all_gmail_connections.apply_async()
        return {"status": "queued", "task": "poll_all_gmail_connections"}
    except Exception as exc:
        # Celery unavailable — run inline (GitHub Actions keeps Render awake)
        try:
            import asyncio
            from app.services.ingestion.gmail_poller import poll_all_gmail_connections
            result = poll_all_gmail_connections()
            return {"status": "completed_inline", "result": str(result)}
        except Exception as exc2:
            return {"status": "error", "detail": str(exc2)}
