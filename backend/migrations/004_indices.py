"""
Migration 004 – add users table indices and notifications sent_at index.
Run via: alembic upgrade head  (or apply manually)
"""

# Revision identifiers
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade(op=None):
    sql = """
    CREATE INDEX IF NOT EXISTS idx_users_phone   ON users (phone);
    CREATE INDEX IF NOT EXISTS idx_users_email   ON users (email);
    CREATE INDEX IF NOT EXISTS idx_users_role    ON users (role);
    CREATE INDEX IF NOT EXISTS idx_notif_sent_at ON notifications (sent_at DESC);
    CREATE INDEX IF NOT EXISTS idx_notif_match   ON notifications (match_id);
    CREATE INDEX IF NOT EXISTS idx_audit_entity  ON audit_log (entity, entity_id);
    """
    if op:
        op.execute(sql)
    else:
        from app.core.db import engine
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text(sql))


def downgrade(op=None):
    pass


if __name__ == "__main__":
    upgrade()
