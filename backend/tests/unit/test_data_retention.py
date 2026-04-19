"""Unit tests for app.services.maintenance.data_retention.

We test the constants and the public `purge_old_data` Celery task by mocking
`_purge_async` entirely.  This avoids importing the ORM models (which use
Python 3.10+ syntax incompatible with the test environment's Python 3.8).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_RESULT = {
    "run_at": datetime.now(timezone.utc).isoformat(),
    "emails_deleted": 3,
    "deadlines_deleted": 1,
    "reminders_deleted": 2,
}


def _make_purge_coro():
    """Return an async function that yields SAMPLE_RESULT."""
    async def _fake_purge():
        return SAMPLE_RESULT
    return _fake_purge


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_retention_constants_match_defaults():
    """EMAIL/DEADLINE/REMINDER retention windows must match Settings defaults."""
    from app.services.maintenance import data_retention
    assert data_retention.EMAIL_RETENTION_DAYS == 90
    assert data_retention.DEADLINE_RETENTION_DAYS == 365
    assert data_retention.REMINDER_RETENTION_DAYS == 365


# ---------------------------------------------------------------------------
# purge_old_data task behaviour (via mocked _purge_async)
# ---------------------------------------------------------------------------

def test_purge_task_returns_emails_deleted():
    from app.services.maintenance import data_retention
    with patch.object(data_retention, "_purge_async", _make_purge_coro()):
        result = data_retention.purge_old_data()
    assert result["emails_deleted"] == 3


def test_purge_task_returns_deadlines_deleted():
    from app.services.maintenance import data_retention
    with patch.object(data_retention, "_purge_async", _make_purge_coro()):
        result = data_retention.purge_old_data()
    assert result["deadlines_deleted"] == 1


def test_purge_task_returns_reminders_deleted():
    from app.services.maintenance import data_retention
    with patch.object(data_retention, "_purge_async", _make_purge_coro()):
        result = data_retention.purge_old_data()
    assert result["reminders_deleted"] == 2


def test_purge_task_result_has_run_at():
    from app.services.maintenance import data_retention
    with patch.object(data_retention, "_purge_async", _make_purge_coro()):
        result = data_retention.purge_old_data()
    assert "run_at" in result
    # Should be a parseable ISO timestamp
    parsed = datetime.fromisoformat(result["run_at"])
    assert parsed.tzinfo is not None
