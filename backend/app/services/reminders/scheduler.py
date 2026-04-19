from __future__ import annotations

import uuid
from datetime import datetime, timezone

import redis as redis_lib

SORTED_SET_KEY = "reminders:pending"


class ReminderScheduler:
    """
    Manages reminder scheduling via a Redis sorted set.
    Score = Unix timestamp (UTC) when the reminder should fire.
    """

    def __init__(self, redis_client: redis_lib.Redis) -> None:
        self._redis = redis_client

    def schedule(self, reminder_id: uuid.UUID, fire_at: datetime) -> None:
        """Add or update a reminder in the sorted set."""
        if fire_at.tzinfo is None:
            fire_at = fire_at.replace(tzinfo=timezone.utc)
        score = fire_at.timestamp()
        self._redis.zadd(SORTED_SET_KEY, {str(reminder_id): score})

    def cancel(self, reminder_id: uuid.UUID) -> None:
        """Remove a reminder from the sorted set."""
        self._redis.zrem(SORTED_SET_KEY, str(reminder_id))

    def snooze(self, reminder_id: uuid.UUID, until: datetime) -> None:
        """Update a reminder's fire time (re-schedule)."""
        self.schedule(reminder_id, until)

    def get_due(self, now: datetime | None = None, batch_size: int = 100) -> list[str]:
        """
        Return reminder IDs whose scheduled time is <= now.
        Does NOT remove them — caller must call mark_processed().
        """
        if now is None:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        score = now.timestamp()
        result = self._redis.zrangebyscore(SORTED_SET_KEY, 0, score, start=0, num=batch_size)
        return [r.decode() if isinstance(r, bytes) else r for r in result]

    def mark_processed(self, reminder_ids: list[str]) -> None:
        """Atomically remove all processed reminder IDs from the sorted set."""
        if not reminder_ids:
            return
        pipe = self._redis.pipeline()
        for rid in reminder_ids:
            pipe.zrem(SORTED_SET_KEY, rid)
        pipe.execute()
