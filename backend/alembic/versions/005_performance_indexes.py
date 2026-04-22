"""Add performance indexes for high-frequency queries.

Revision ID: 005
Revises: 004
Create Date: 2026-04-22

These partial indexes dramatically speed up the three hottest query patterns:
- Rescue task finding unprocessed emails
- Dispatcher finding pending reminders by schedule time
- Dashboard finding pending deadlines per user
- Beat scheduler finding connections due for polling
"""
from __future__ import annotations

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_extracted_emails_unprocessed
          ON extracted_emails(connection_id, created_at)
          WHERE is_processed = FALSE AND is_spam = FALSE;
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_reminders_pending_schedule
          ON reminders(scheduled_at)
          WHERE status = 'pending';
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_deadlines_active_user
          ON deadlines(user_id, due_at)
          WHERE status = 'pending';
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_connections_active_poll
          ON email_connections(last_polled_at)
          WHERE is_active = TRUE;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_extracted_emails_unprocessed;")
    op.execute("DROP INDEX IF EXISTS idx_reminders_pending_schedule;")
    op.execute("DROP INDEX IF EXISTS idx_deadlines_active_user;")
    op.execute("DROP INDEX IF EXISTS idx_connections_active_poll;")
