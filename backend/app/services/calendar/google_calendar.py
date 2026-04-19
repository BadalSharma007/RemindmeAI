"""Google Calendar integration — create deadline events.

Uses the OAuth 2.0 Bearer token already obtained via Gmail OAuth (scope
``https://www.googleapis.com/auth/calendar.events``).  No additional
service-account credentials are required; the user's own token is reused.

The token must have the ``calendar.events`` scope.  If the scope was not
requested during the initial Gmail consent, the request will receive a 403
and ``CalendarScopeError`` is raised so the caller can prompt re-consent.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

CALENDAR_EVENTS_URL = (
    "https://www.googleapis.com/calendar/v3/calendars/primary/events"
)

# Reminder: 10 minutes before the event (Google Calendar popup)
_DEFAULT_REMINDER_MINUTES = 10


class CalendarScopeError(Exception):
    """Raised when the access token lacks the calendar.events scope."""


class GoogleCalendarClient:
    """Thin async wrapper around the Google Calendar API v3.

    Parameters
    ----------
    access_token:
        A valid OAuth 2.0 Bearer token with ``calendar.events`` scope.
    """

    def __init__(self, access_token: str) -> None:
        self._token = access_token

    async def create_deadline_event(
        self,
        title: str,
        due_at: datetime,
        description: str = "",
        reminder_minutes: int = _DEFAULT_REMINDER_MINUTES,
    ) -> str:
        """Create a timed event on the user's primary Google Calendar.

        Parameters
        ----------
        title:
            Event title (e.g. "Deadline: Submit Q2 report").
        due_at:
            UTC datetime for the event start/end (treated as a 30-min block).
        description:
            Optional body text shown in the event detail view.
        reminder_minutes:
            Minutes before the event for the popup reminder.

        Returns
        -------
        The ``id`` of the newly created Calendar event (str).

        Raises
        ------
        CalendarScopeError  — 403 from the API (missing scope).
        httpx.HTTPStatusError — any other non-2xx response.
        """
        due_utc = due_at.astimezone(timezone.utc)
        end_utc = due_utc.replace(
            minute=due_utc.minute + 30 if due_utc.minute <= 29 else 0,
            hour=due_utc.hour + (1 if due_utc.minute > 29 else 0),
        )

        payload: dict[str, Any] = {
            "summary": title[:500],
            "description": description[:2000],
            "start": {
                "dateTime": due_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "timeZone": "UTC",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": reminder_minutes},
                ],
            },
            "source": {
                "title": "RemindmeAI",
                "url": "https://remindmeai.app",
            },
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                CALENDAR_EVENTS_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code == 403:
            raise CalendarScopeError(
                "Access token lacks calendar.events scope. Re-consent required."
            )
        resp.raise_for_status()

        event_id: str = resp.json()["id"]
        logger.info("Created Calendar event %s for deadline '%s'", event_id, title)
        return event_id

    async def delete_event(self, event_id: str) -> None:
        """Delete a previously created event (e.g. when a deadline is dismissed)."""
        url = f"{CALENDAR_EVENTS_URL.rsplit('/events', 1)[0]}/events/{event_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(
                url,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        # 204 = deleted, 410 = already gone — both are acceptable
        if resp.status_code not in (204, 410):
            resp.raise_for_status()
        logger.info("Deleted Calendar event %s", event_id)


@dataclass
class CalendarEventResult:
    event_id: str
    title: str
    due_at: datetime
