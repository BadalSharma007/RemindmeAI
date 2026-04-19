"""Unit tests for Pydantic schemas — no external dependencies."""
from datetime import datetime, timezone, timedelta
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.deadline import DeadlineRead, DeadlinePatch
from app.schemas.reminder import ReminderRead, SnoozeRequest
from app.schemas.preference import PreferencePatch
from app.schemas.dashboard import DashboardStats


def _make_deadline_read(**kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "title": "Test deadline",
        "due_at": datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
        "confidence_score": 0.8,
        "status": "pending",
    }
    defaults.update(kwargs)
    return defaults


def test_deadline_read_requires_timezone_aware_due_at():
    """due_at without tzinfo must raise ValidationError."""
    data = _make_deadline_read(due_at=datetime(2026, 4, 1, 12, 0))  # naive datetime
    with pytest.raises(ValidationError):
        DeadlineRead(**data)


def test_snooze_request_rejects_past_datetime():
    """snooze_until in the past must raise ValidationError."""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    with pytest.raises(ValidationError):
        SnoozeRequest(snooze_until=past)


def test_preference_patch_partial_update():
    """PreferencePatch should only include provided fields."""
    patch = PreferencePatch(timezone="America/New_York")
    dumped = patch.model_dump(exclude_unset=True)
    assert "timezone" in dumped
    assert "reminder_lead_minutes" not in dumped


def test_dashboard_stats_defaults_to_zeros():
    """DashboardStats with no args should default all counts to 0."""
    stats = DashboardStats()
    assert stats.total_deadlines == 0
    assert stats.pending_deadlines == 0
    assert stats.upcoming_reminders == 0
    assert stats.emails_processed_today == 0
    assert stats.connected_accounts == 0
