from __future__ import annotations

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_deadlines: int = 0
    pending_deadlines: int = 0
    upcoming_reminders: int = 0
    emails_processed_today: int = 0
    connected_accounts: int = 0
