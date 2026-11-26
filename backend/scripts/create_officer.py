"""
Secure production CLI to create the initial officer account.

Usage:
    OFFICER_NAME="Block Officer" OFFICER_EMAIL="officer@punjab.gov.in" \
    OFFICER_PHONE="+919800000001" OFFICER_PASSWORD="<strong-password>" \
    python scripts/create_officer.py
"""
import getpass
import os
import sys

from sqlalchemy import text

from app.core.db import engine
from app.core.security import hash_password


def main() -> None:
    name = os.environ.get("OFFICER_NAME") or input("Officer name: ").strip()
    email = os.environ.get("OFFICER_EMAIL") or input("Officer email: ").strip()
    phone = os.environ.get("OFFICER_PHONE") or input("Officer phone (optional): ").strip() or None
    password = os.environ.get("OFFICER_PASSWORD") or getpass.getpass("Officer password (min 10 chars): ")

    if not name or not email:
        print("Error: OFFICER_NAME and OFFICER_EMAIL are required.", file=sys.stderr)
        sys.exit(1)
    if len(password) < 10:
        print("Error: password must be at least 10 characters.", file=sys.stderr)
        sys.exit(1)

    pw_hash = hash_password(password)
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO users (name, phone, email, password_hash, role, language)
                VALUES (:name, :phone, :email, :pw, 'officer', 'en')
                ON CONFLICT (email) DO NOTHING
            """),
            {"name": name, "phone": phone, "email": email, "pw": pw_hash},
        )
    print(f"Officer account ensured for {email}.")


if __name__ == "__main__":
    main()
