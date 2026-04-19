"""Unit tests for app.services.calendar.google_calendar — no network calls."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.calendar.google_calendar import (
    CalendarScopeError,
    GoogleCalendarClient,
)

_DUE = datetime(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc)
_TOKEN = "fake-access-token"


def _make_mock_client(status_code: int, json_body: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.raise_for_status = MagicMock(
        side_effect=None if status_code < 400 else Exception("HTTP error")
    )
    mock_resp.json.return_value = json_body

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.delete = AsyncMock(return_value=mock_resp)
    return mock_client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_event_returns_event_id():
    mock_client = _make_mock_client(200, {"id": "event-abc-123"})
    with patch("app.services.calendar.google_calendar.httpx.AsyncClient", return_value=mock_client):
        cal = GoogleCalendarClient(_TOKEN)
        event_id = await cal.create_deadline_event(
            title="Submit Q2 report",
            due_at=_DUE,
        )
    assert event_id == "event-abc-123"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_create_event_payload_contains_title():
    captured_payload = {}

    async def _fake_post(url, json=None, headers=None):
        captured_payload.update(json or {})
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"id": "ev-1"}
        return mock_resp

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = _fake_post

    with patch("app.services.calendar.google_calendar.httpx.AsyncClient", return_value=mock_client):
        cal = GoogleCalendarClient(_TOKEN)
        await cal.create_deadline_event(title="My Deadline", due_at=_DUE)

    assert captured_payload["summary"] == "My Deadline"
    assert "start" in captured_payload
    assert "reminders" in captured_payload


@pytest.mark.asyncio
async def test_create_event_raises_scope_error_on_403():
    mock_resp = MagicMock()
    mock_resp.status_code = 403

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("app.services.calendar.google_calendar.httpx.AsyncClient", return_value=mock_client):
        cal = GoogleCalendarClient(_TOKEN)
        with pytest.raises(CalendarScopeError):
            await cal.create_deadline_event(title="x", due_at=_DUE)


@pytest.mark.asyncio
async def test_title_truncated_to_500():
    captured = {}

    async def _fake_post(url, json=None, headers=None):
        captured.update(json or {})
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"id": "ev-1"}
        return mock_resp

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = _fake_post

    with patch("app.services.calendar.google_calendar.httpx.AsyncClient", return_value=mock_client):
        cal = GoogleCalendarClient(_TOKEN)
        await cal.create_deadline_event(title="T" * 1000, due_at=_DUE)

    assert len(captured["summary"]) <= 500
