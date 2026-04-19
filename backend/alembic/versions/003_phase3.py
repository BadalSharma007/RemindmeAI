"""Phase 3 schema additions.

Adds:
- extracted_emails.spam_score     — float nullable: 0.0–1.0 spam probability
- extracted_emails.is_spam        — bool default False: spam/marketing flag
- deadlines.calendar_event_id     — varchar(255) nullable: Google Calendar event ID

Revision ID: 003
Revises: 002
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # extracted_emails — spam detection columns
    op.add_column(
        "extracted_emails",
        sa.Column("spam_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "extracted_emails",
        sa.Column("is_spam", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # deadlines — Google Calendar integration
    op.add_column(
        "deadlines",
        sa.Column("calendar_event_id", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("deadlines", "calendar_event_id")
    op.drop_column("extracted_emails", "is_spam")
    op.drop_column("extracted_emails", "spam_score")
