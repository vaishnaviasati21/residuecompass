"""
Auth router – /api/v1/auth/login and /api/v1/auth/register.

Roles:
  officer – sees everything; created by another officer or via seed
  farmer  – sees only their own village data
  buyer   – sees only matches and buyers related to their account
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.core.errors import api_error, not_found
from app.core.security import create_access_token, hash_password, verify_password
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _find_user(conn, username: str):
    """Lookup by phone or email (whichever matches)."""
    return conn.execute(
        text("""
            SELECT id, name, role, password_hash, village_id, buyer_id
            FROM users
            WHERE phone = :u OR email = :u
            LIMIT 1
        """),
        {"u": username},
    ).mappings().first()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    with db.connection() as conn:
        user = _find_user(conn, body.username)
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise api_error(401, "INVALID_CREDENTIALS",
                        "Incorrect username or password.", "username")
    token = create_access_token({
        "sub": str(user["id"]),
        "role": user["role"],
        "village_id": user["village_id"],
        "buyer_id": user["buyer_id"],
    })
    return TokenResponse(
        access_token=token,
        role=user["role"],
        user_id=user["id"],
        name=user["name"],
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """
    Self-registration for farmers and buyers.
    Officers must be seeded or created by another officer (not via this endpoint).
    """
    if body.role == "officer":
        raise api_error(403, "OFFICER_REGISTRATION_CLOSED",
                        "Officer accounts are created by administrators only.")
    if body.role == "farmer" and not body.village_id:
        raise api_error(400, "MISSING_FIELD", "village_id is required for farmers.", "village_id")
    if body.role == "buyer" and not body.buyer_id:
        raise api_error(400, "MISSING_FIELD", "buyer_id is required for buyers.", "buyer_id")

    with db.connection() as conn:
        # Uniqueness check
        exists = conn.execute(
            text("SELECT 1 FROM users WHERE phone=:ph OR email=:em LIMIT 1"),
            {"ph": body.phone, "em": body.email},
        ).first()
        if exists:
            raise api_error(409, "USER_EXISTS",
                            "A user with this phone or email already exists.")

        result = conn.execute(
            text("""
                INSERT INTO users (name, phone, email, password_hash, role, village_id, buyer_id, language)
                VALUES (:name, :phone, :email, :pw, :role, :vid, :bid, :lang)
                RETURNING id
            """),
            {
                "name": body.name, "phone": body.phone, "email": body.email,
                "pw": hash_password(body.password), "role": body.role,
                "vid": body.village_id, "bid": body.buyer_id, "lang": body.language,
            },
        )
        conn.commit()
        user_id = result.scalar()

    token = create_access_token({
        "sub": str(user_id),
        "role": body.role,
        "village_id": body.village_id,
        "buyer_id": body.buyer_id,
    })
    return TokenResponse(access_token=token, role=body.role, user_id=user_id, name=body.name)


@router.get("/me", tags=["auth"])
def me(user: CurrentUser, db: Session = Depends(get_db)):
    """Return own profile. Used by the frontend to restore session."""
    uid = int(user.get("sub", 0))
    with db.connection() as conn:
        row = conn.execute(
            text("""
                SELECT id, name, phone, email, role, village_id, buyer_id, language
                FROM users
                WHERE id = :uid
            """),
            {"uid": uid},
        ).mappings().first()
    if row is None:
        raise not_found("user", "user_id")
    return dict(row)
