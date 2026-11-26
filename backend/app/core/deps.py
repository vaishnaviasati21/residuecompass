"""
FastAPI dependency injection helpers.

Usage in a router:
    from app.core.deps import require_role, CurrentUser
    ...
    @router.get("/sensitive")
    def view(user: CurrentUser = Depends(require_role("officer"))):
        ...
"""
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.errors import unauthenticated, forbidden
from app.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2_scheme)) -> dict:
    """Return the decoded token payload or raise 401."""
    if not token:
        raise unauthenticated()
    payload = decode_access_token(token)
    if payload is None:
        raise unauthenticated()
    return payload


def require_role(*roles: str):
    """
    Factory that returns a dependency enforcing role membership.

    Example:
        Depends(require_role("officer", "buyer"))
    """
    def _check(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise forbidden(f"This endpoint requires one of: {', '.join(roles)}.")
        return user
    return _check


# Convenience type aliases used in router signatures
CurrentUser = Annotated[dict, Depends(get_current_user)]
OfficerUser = Annotated[dict, Depends(require_role("officer"))]
FarmerUser  = Annotated[dict, Depends(require_role("farmer", "officer"))]
BuyerUser   = Annotated[dict, Depends(require_role("buyer", "officer"))]
