from fastapi import HTTPException


def api_error(status: int, code: str, message: str, field: str | None = None):
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message, "field": field}},
    )