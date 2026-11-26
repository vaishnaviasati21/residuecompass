"""Add partial unique index for concurrency-safe notification idempotency.

Revision ID: 0004_notification_idempotency
Revises: 0003_indices
Create Date: 2026-11-26
"""
from alembic import op

revision = "0004_notification_idempotency"
down_revision = "0003_indices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_notifications_match_user_active
        ON notifications (match_id, COALESCE(user_id, -1))
        WHERE status IN ('queued', 'sent');
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_notifications_match_user_active;")
