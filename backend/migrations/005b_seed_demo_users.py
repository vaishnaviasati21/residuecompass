"""
Migration 005 also seeds demo farmer and buyer users.
Run with:  python migrations/005_seed_officer.py
"""

revision = "005b"
down_revision = "005"


def upgrade(op=None):
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


if __name__ == "__main__":
    upgrade()
