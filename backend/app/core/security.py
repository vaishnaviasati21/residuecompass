"""
JWT creation + verification, password hashing.
Depends on python-jose and passlib[bcrypt].
Graceful fallback when libraries are absent (lets tests run without extras).
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings

# ── Optional imports with graceful degradation ────────────────────────────
try:
    from jose import JWTError, jwt as _jwt
    _JOSE_OK = True
except ImportError:
    _JOSE_OK = False

try:
    from passlib.context import CryptContext
    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    _PASSLIB_OK = True
except ImportError:
    _PASSLIB_OK = False


# ── Password helpers ──────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    if not _PASSLIB_OK:
        return plain   # development-only fallback, never use in prod
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    if not _PASSLIB_OK:
        return plain == hashed
    return _pwd_ctx.verify(plain, hashed)


# ── Token helpers ─────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Return a signed JWT containing *data* plus an expiry claim."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    if not _JOSE_OK:
        # Simple base64 fallback for demo without python-jose installed
        import base64, json
        return base64.urlsafe_b64encode(json.dumps(to_encode, default=str).encode()).decode()
    return _jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Return the payload dict or None if invalid/expired."""
    if not _JOSE_OK:
        import base64, json
        try:
            payload = json.loads(base64.urlsafe_b64decode(token + "=="))
            exp = payload.get("exp")
            if exp and datetime.fromisoformat(str(exp).replace("Z", "+00:00")) < datetime.now(timezone.utc):
                return None
            return payload
        except Exception:
            return None
    try:
        return _jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except Exception:
        return None
