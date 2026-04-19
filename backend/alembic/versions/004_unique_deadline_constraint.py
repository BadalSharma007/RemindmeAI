"""Add unique constraint to prevent duplicate deadlines per email+due_at

Revision ID: 004
Revises: 003
Create Date: 2026-04-19
"""
from alembic import op

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Remove existing duplicates first — keep the one with lowest UUID (earliest created)
    op.execute("""
        DELETE FROM deadlines a
        USING deadlines b
        WHERE a.id > b.id
        AND a.extracted_email_id = b.extracted_email_id
        AND DATE_TRUNC('minute', a.due_at) = DATE_TRUNC('minute', b.due_at)
    """)

    op.create_unique_constraint(
        'uq_deadline_email_due',
        'deadlines',
        ['extracted_email_id', 'due_at'],
    )


def downgrade():
    op.drop_constraint('uq_deadline_email_due', 'deadlines', type_='unique')
