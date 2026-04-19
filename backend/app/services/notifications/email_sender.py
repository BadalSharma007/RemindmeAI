from __future__ import annotations

import logging
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


class SESEmailSender:
    """Send reminder emails via AWS Simple Email Service."""

    def __init__(self) -> None:
        self._client = boto3.client(
            "ses",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        self._sender = settings.ses_sender_email

    async def send_reminder_email(
        self,
        to_address: str,
        deadline_title: str,
        due_at: datetime,
        reminder_id: str,
    ) -> None:
        """Send an HTML reminder email. Raises on SES failure."""
        subject = f"Reminder: {deadline_title[:80]}"
        html_body = self._build_html_body(deadline_title, due_at, reminder_id)
        text_body = self._build_text_body(deadline_title, due_at)

        try:
            self._client.send_email(
                Source=self._sender,
                Destination={"ToAddresses": [to_address]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                        "Text": {"Data": text_body, "Charset": "UTF-8"},
                    },
                },
            )
            logger.info("Sent reminder email to %s for deadline %r", to_address, deadline_title)
        except ClientError as exc:
            logger.error("SES error sending to %s: %s", to_address, exc)
            raise

    def _build_html_body(self, title: str, due_at: datetime, reminder_id: str) -> str:
        formatted_due = due_at.strftime("%A, %B %d, %Y at %I:%M %p UTC")
        return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: #f0f4ff; border-left: 4px solid #4f46e5; padding: 20px; border-radius: 8px;">
    <h2 style="color: #1e1b4b; margin-top: 0;">⏰ Reminder</h2>
    <p style="font-size: 18px; color: #374151;"><strong>{title}</strong></p>
    <p style="color: #6b7280;">Due: <strong>{formatted_due}</strong></p>
  </div>
  <p style="color: #9ca3af; font-size: 12px; margin-top: 30px;">
    Sent by RemindmeAI &bull;
    <a href="{settings.frontend_url}/reminders/{reminder_id}/dismiss" style="color: #9ca3af;">Dismiss</a>
  </p>
</body>
</html>
"""

    def _build_text_body(self, title: str, due_at: datetime) -> str:
        formatted_due = due_at.strftime("%A, %B %d, %Y at %I:%M %p UTC")
        return f"Reminder: {title}\nDue: {formatted_due}\n\nSent by RemindmeAI"
