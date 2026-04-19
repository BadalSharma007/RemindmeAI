"""Unit tests for app.services.notifications.push_sender — no Firebase network calls.

Uses sys.modules injection so the tests run without firebase_admin installed.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.services.notifications.push_sender import FCMSender, reset_firebase_cache


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_cache():
    reset_firebase_cache()
    yield
    reset_firebase_cache()


SAMPLE_DUE = datetime(2026, 4, 10, 17, 0, 0, tzinfo=timezone.utc)
SAMPLE_RID = "123e4567-e89b-12d3-a456-426614174000"


def _inject_firebase(monkeypatch):
    """
    Inject a fake firebase_admin package into sys.modules so that
    `from firebase_admin import messaging` inside push_sender returns
    the mock we control.

    Returns the mock_messaging object to assert on.
    """
    mock_messaging = MagicMock(name="firebase_admin.messaging")
    mock_messaging.send.return_value = "projects/x/messages/fake-id"

    mock_fa = MagicMock(name="firebase_admin")
    # Explicitly link .messaging so `from firebase_admin import messaging` resolves correctly
    mock_fa.messaging = mock_messaging

    monkeypatch.setitem(sys.modules, "firebase_admin", mock_fa)
    monkeypatch.setitem(sys.modules, "firebase_admin.messaging", mock_messaging)
    return mock_messaging


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_push_calls_messaging_send(monkeypatch):
    """Happy path: messaging.send is called once with a token-bearing message."""
    import app.services.notifications.push_sender as module

    monkeypatch.setattr(module, "_get_firebase_app", lambda: object())
    mock_messaging = _inject_firebase(monkeypatch)

    sender = FCMSender()
    await sender.send_push_notification(
        fcm_token="device-token-abc",
        deadline_title="Submit Q2 report",
        due_at=SAMPLE_DUE,
        reminder_id=SAMPLE_RID,
    )

    assert mock_messaging.send.call_count == 1


@pytest.mark.asyncio
async def test_raises_when_firebase_not_initialised(monkeypatch):
    """RuntimeError raised if Firebase app is not configured (returns None)."""
    import app.services.notifications.push_sender as module

    monkeypatch.setattr(module, "_get_firebase_app", lambda: None)

    sender = FCMSender()
    with pytest.raises(RuntimeError, match="Firebase not initialised"):
        await sender.send_push_notification(
            fcm_token="token",
            deadline_title="Title",
            due_at=SAMPLE_DUE,
            reminder_id=SAMPLE_RID,
        )


@pytest.mark.asyncio
async def test_deadline_title_truncated_to_80(monkeypatch):
    """Titles longer than 80 chars must be truncated in the Notification body."""
    import app.services.notifications.push_sender as module

    monkeypatch.setattr(module, "_get_firebase_app", lambda: object())
    mock_messaging = _inject_firebase(monkeypatch)

    notifications_built: list[str] = []

    def _capture_notification(title: str, body: str):  # noqa: ARG001
        notifications_built.append(body)
        return MagicMock()

    mock_messaging.Notification.side_effect = _capture_notification

    sender = FCMSender()
    await sender.send_push_notification(
        fcm_token="tok",
        deadline_title="X" * 200,
        due_at=SAMPLE_DUE,
        reminder_id=SAMPLE_RID,
    )

    assert len(notifications_built) == 1
    # Body format: "{title[:80]} · Due {date}"
    title_part = notifications_built[0].split(" · ")[0]
    assert len(title_part) <= 80


def test_reset_firebase_cache_clears_singleton(monkeypatch):
    """reset_firebase_cache() sets _firebase_app back to None."""
    import app.services.notifications.push_sender as module

    module._firebase_app = object()  # simulate initialised state
    reset_firebase_cache()
    assert module._firebase_app is None
