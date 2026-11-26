"""Add users, notifications, and audit_log indices.

Revision ID: 0003_indices
Revises: 0002_extra_columns
Create Date: 2026-11-26
"""
from alembic import op

revision = "0003_indices"
down_revision = "0002_extra_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_phone   ON users (phone);
        CREATE INDEX IF NOT EXISTS idx_users_email   ON users (email);
        CREATE INDEX IF NOT EXISTS idx_users_role    ON users (role);
        CREATE INDEX IF NOT EXISTS idx_notif_sent_at ON notifications (sent_at DESC);
        CREATE INDEX IF NOT EXISTS idx_notif_match   ON notifications (match_id);
        CREATE INDEX IF NOT EXISTS idx_audit_entity  ON audit_log (entity, entity_id);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS idx_audit_entity;
        DROP INDEX IF EXISTS idx_notif_match;
        DROP INDEX IF EXISTS idx_notif_sent_at;
        DROP INDEX IF EXISTS idx_users_role;
        DROP INDEX IF EXISTS idx_users_email;
        DROP INDEX IF EXISTS idx_users_phone;
    """)
