"""Phase 2 schema additions.

Adds:
- users.fcm_token         — FCM device registration token for push notifications
- deadlines.user_confirmed — nullable bool: user feedback on deadline accuracy
- deadlines.classifier_tier — tinyint: 1 = rule-based, 2 = ML (audit column)

Revision ID: 002
Revises: 001
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users ---
    op.add_column(
        "users",
        sa.Column("fcm_token", sa.String(length=500), nullable=True, comment="FCM device registration token"),
    )

    # --- deadlines ---
    op.add_column(
        "deadlines",
        sa.Column(
            "user_confirmed",
            sa.Boolean(),
            nullable=True,
            comment="True=correctly identified, False=false positive, NULL=no feedback",
        ),
    )
    op.add_column(
        "deadlines",
        sa.Column(
            "classifier_tier",
            sa.SmallInteger(),
            nullable=True,
            comment="1=rule-based, 2=ML zero-shot",
        ),
    )


def downgrade() -> None:
    op.drop_column("deadlines", "classifier_tier")
    op.drop_column("deadlines", "user_confirmed")
    op.drop_column("users", "fcm_token")
