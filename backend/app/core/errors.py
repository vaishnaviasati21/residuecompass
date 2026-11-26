"""
Standardised error helper.
All errors use the same envelope so the frontend can parse them reliably.

Shape:
  { "detail": { "error": { "code": "...", "message": "...", "field": null | "fieldname" } } }
"""
from fastapi import HTTPException


def api_error(status: int, code: str, message: str, field: str | None = None) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message, "field": field}},
    )


# ── Named shortcuts so callers stay readable ──────────────────────────────

def not_found(entity: str, field: str = "id") -> HTTPException:
    return api_error(404, f"{entity.upper()}_NOT_FOUND", f"No {entity} with this ID.", field)


def forbidden(message: str = "You do not have permission for this action.") -> HTTPException:
    return api_error(403, "FORBIDDEN", message)


def unauthenticated() -> HTTPException:
    return api_error(401, "UNAUTHENTICATED", "Please log in to continue.")


def bad_request(code: str, message: str, field: str | None = None) -> HTTPException:
    return api_error(400, code, message, field)
