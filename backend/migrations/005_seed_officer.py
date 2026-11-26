"""
Demo-only seed officer user (password: officer123).
Refuses to run when DEMO_MODE=false so demo credentials never enter production.
"""

revision = "005"
down_revision = "004"


def upgrade(op=None):
    from app.core.config import settings
    if not settings.DEMO_MODE:
        raise RuntimeError("Refusing to seed demo officer account when DEMO_MODE=false.")

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
