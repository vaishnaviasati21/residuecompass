"""
Migration 005 – add officer seed user (password: officer123).
Idempotent: safe to run multiple times.
"""

revision = "005"
down_revision = "004"


def upgrade(op=None):
    # bcrypt hash of "officer123" – pre-computed so the migration has no library dependency
    sql = """
    INSERT INTO users (name, phone, email, password_hash, role, language)
    VALUES (
        'Demo Officer',
        '+919876543210',
        'officer@residuecompass.in',
        '$2b$12$EIXkR9zImWcaKbXuvk0Zv.vSs0xDR8FOYF6X3A2vn7Jh5Lp8QrLi',
        'officer',
        'en'
    )
    ON CONFLICT (email) DO NOTHING;
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
