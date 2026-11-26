"""
Demo-only seed farmer and buyer users.
Refuses to run when DEMO_MODE=false so demo credentials never enter production.
"""

revision = "005b"
down_revision = "005"


def upgrade(op=None):
    from app.core.config import settings
    if not settings.DEMO_MODE:
        raise RuntimeError("Refusing to seed demo farmer/buyer accounts when DEMO_MODE=false.")

    sql = """
    INSERT INTO users (name, phone, email, password_hash, role, village_id, language)
    VALUES (
        'Demo Farmer',
        '+919876543211',
        'farmer@residuecompass.in',
        '$2b$12$EIXkR9zImWcaKbXuvk0Zv.vSs0xDR8FOYF6X3A2vn7Jh5Lp8QrLi',
        'farmer',
        'PB-SNG-0142',
        'pa'
    )
    ON CONFLICT (email) DO NOTHING;

    INSERT INTO users (name, phone, email, password_hash, role, buyer_id, language)
    VALUES (
        'Demo Buyer',
        '+919876543212',
        'buyer@residuecompass.in',
        '$2b$12$EIXkR9zImWcaKbXuvk0Zv.vSs0xDR8FOYF6X3A2vn7Jh5Lp8QrLi',
        'buyer',
        'B-012',
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
