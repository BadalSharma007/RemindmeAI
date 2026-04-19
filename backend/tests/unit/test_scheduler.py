"""Unit tests for app.services.reminders.scheduler — uses fakeredis."""
import uuid
from datetime import datetime, timedelta, timezone

import fakeredis
import pytest

from app.services.reminders.scheduler import ReminderScheduler, SORTED_SET_KEY


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis()


@pytest.fixture
def scheduler(redis_client):
    return ReminderScheduler(redis_client)


def test_schedule_adds_to_sorted_set(scheduler, redis_client):
    rid = uuid.uuid4()
    fire_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
    scheduler.schedule(rid, fire_at)
    score = redis_client.zscore(SORTED_SET_KEY, str(rid))
    assert score is not None
    assert abs(score - fire_at.timestamp()) < 1


def test_get_due_returns_only_past_scores(scheduler):
    past_id = uuid.uuid4()
    future_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    scheduler.schedule(past_id, now - timedelta(minutes=5))
    scheduler.schedule(future_id, now + timedelta(hours=2))

    due = scheduler.get_due(now=now)
    assert str(past_id) in due
    assert str(future_id) not in due


def test_cancel_removes_from_set(scheduler, redis_client):
    rid = uuid.uuid4()
    fire_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    scheduler.schedule(rid, fire_at)
    scheduler.cancel(rid)
    score = redis_client.zscore(SORTED_SET_KEY, str(rid))
    assert score is None


def test_snooze_updates_score(scheduler, redis_client):
    rid = uuid.uuid4()
    original = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
    snoozed = datetime(2026, 4, 1, 14, 0, 0, tzinfo=timezone.utc)

    scheduler.schedule(rid, original)
    scheduler.snooze(rid, snoozed)

    score = redis_client.zscore(SORTED_SET_KEY, str(rid))
    assert abs(score - snoozed.timestamp()) < 1


def test_mark_processed_bulk_removes(scheduler, redis_client):
    ids = [uuid.uuid4() for _ in range(3)]
    fire_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    for rid in ids:
        scheduler.schedule(rid, fire_at)

    scheduler.mark_processed([str(i) for i in ids])

    for rid in ids:
        assert redis_client.zscore(SORTED_SET_KEY, str(rid)) is None
