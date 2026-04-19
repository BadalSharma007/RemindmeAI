"""Phase 2 — Firebase Cloud Messaging (FCM) push notification sender.

Initialises the Firebase Admin SDK once from the JSON credentials stored in
``settings.fcm_service_account_json`` (full JSON string, not a file path).
Falls back gracefully when FCM is not configured.

Usage::

    sender = FCMSender()
    await sender.send_push_notification(
        fcm_token=user.fcm_token,
        deadline_title="Submit Q2 report",
        due_at=datetime(2026, 4, 10, 17, 0, tzinfo=timezone.utc),
        reminder_id=str(reminder.id),
    )
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

_firebase_app = None          # firebase_admin.App | False (tried, unavailable)
_firebase_lock = threading.Lock()


def _get_firebase_app():
    """Return the lazy-initialised Firebase app, or None if not configured."""
    global _firebase_app
    if _firebase_app is None:
        with _firebase_lock:
            if _firebase_app is None:
                try:
                    import firebase_admin  # noqa: PLC0415
                    from firebase_admin import credentials  # noqa: PLC0415

                    from app.config import settings  # noqa: PLC0415

                    if not settings.fcm_service_account_json:
                        logger.warning(
                            "FCM not configured: FCM_SERVICE_ACCOUNT_JSON is empty. "
                            "Push notifications will be skipped."
                        )
                        _firebase_app = False
                    else:
                        cred_data = json.loads(settings.fcm_service_account_json)
                        cred = credentials.Certificate(cred_data)
                        _firebase_app = firebase_admin.initialize_app(cred)
                        logger.info("Firebase Admin SDK initialised (project: %s)", cred_data.get("project_id"))
                except json.JSONDecodeError as exc:
                    logger.error("Invalid FCM_SERVICE_ACCOUNT_JSON (not valid JSON): %s", exc)
                    _firebase_app = False
                except Exception as exc:  # noqa: BLE001
                    logger.error("Firebase Admin SDK init failed: %s", exc)
                    _firebase_app = False

    return None if _firebase_app is False else _firebase_app


class FCMSender:
    """Send push notifications via Firebase Cloud Messaging."""

    async def send_push_notification(
        self,
        fcm_token: str,
        deadline_title: str,
        due_at: datetime,
        reminder_id: str,
    ) -> None:
        """
        Dispatch an FCM push notification to a single device token.

        Args:
            fcm_token: The device registration token from the client app.
            deadline_title: Short deadline description (truncated to 80 chars).
            due_at: UTC-aware deadline datetime.
            reminder_id: UUID string used in notification data payload.

        Raises:
            RuntimeError: If Firebase is not initialised.
            firebase_admin.exceptions.FirebaseError: On FCM delivery failure.
        """
        app = _get_firebase_app()
        if app is None:
            raise RuntimeError(
                "Firebase not initialised — set FCM_SERVICE_ACCOUNT_JSON env var."
            )

        from firebase_admin import messaging  # noqa: PLC0415

        title_short = deadline_title[:80]
        formatted_due = due_at.strftime("%b %d at %I:%M %p UTC")

        message = messaging.Message(
            token=fcm_token,
            notification=messaging.Notification(
                title="RemindmeAI — Deadline Approaching",
                body=f"{title_short} · Due {formatted_due}",
            ),
            data={
                "reminder_id": reminder_id,
                "due_at": due_at.isoformat(),
                "type": "deadline_reminder",
            },
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    icon="ic_notification",
                    color="#4f46e5",
                    channel_id="reminders",
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title="RemindmeAI — Deadline Approaching",
                            body=f"{title_short} · Due {formatted_due}",
                        ),
                        badge=1,
                        sound="default",
                    ),
                ),
            ),
        )

        try:
            response_id = messaging.send(message, app=app)
            logger.info(
                "FCM push sent (message_id=%s) for reminder %s",
                response_id,
                reminder_id,
            )
        except Exception as exc:
            logger.error("FCM send failed for reminder %s: %s", reminder_id, exc)
            raise


def reset_firebase_cache() -> None:
    """Force next call to re-initialise Firebase (useful in tests)."""
    global _firebase_app
    with _firebase_lock:
        _firebase_app = None
