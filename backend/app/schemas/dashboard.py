from __future__ import annotations

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_deadlines: int = 0
    pending_deadlines: int = 0
    completed_deadlines: int = 0
    upcoming_reminders: int = 0
    emails_processed_today: int = 0
    connected_accounts: int = 0
    total_emails_read: int = 0       # all-time emails fetched across all connections
    important_emails_today: int = 0  # today's non-spam emails (deadline candidates)
