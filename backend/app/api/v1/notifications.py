"""
Notifications router – log of every message sent.
  GET  /notifications       – officer sees all; farmer / buyer see own
  POST /notifications/send  – officer triggers a manual send for a match

Pagination is bounded: limit 1–200, offset ≥ 0.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, OfficerUser
from app.schemas.notification import NotificationList, NotificationOut
from app.notifier.sender import send_notification_for_match

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _row_to_notif(r) -> dict:
    return {
        "id": r["id"],
        "user_id": r["user_id"],
        "match_id": r["match_id"],
        "channel": r["channel"],
        "language": r["language"],
        "body": r["body"],
        "status": r["status"],
        "provider_id": r["provider_id"],
        "sent_at": r["sent_at"],
    }


@router.get("", response_model=NotificationList)
def list_notifications(
    _user: CurrentUser,
    match_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200, description="Max results (1–200)"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    db: Session = Depends(get_db),
):
    """
    List notifications with bounded pagination.
    Officers see all; farmers and buyers see only their own.
    """
    role = _user.get("role")
    user_id = int(_user.get("sub", 0))

    where = "WHERE 1=1"
    params: dict = {"limit": limit, "offset": offset, "uid": user_id}

    if role in ("farmer", "buyer"):
        where += " AND n.user_id = :uid"
    if match_id:
        where += " AND n.match_id = :mid"
        params["mid"] = match_id

    sql = text(f"""
        SELECT n.id, n.user_id, n.match_id, n.channel, n.language,
               n.body, n.status, n.provider_id, n.sent_at
        FROM notifications n
        {where}
        ORDER BY n.sent_at DESC
        LIMIT :limit OFFSET :offset
    """)
    count_sql = text(f"SELECT COUNT(*) FROM notifications n {where}")

    with db.connection() as conn:
        rows = conn.execute(sql, params).mappings().all()
        total = conn.execute(count_sql, params).scalar() or 0

    return {"items": [_row_to_notif(r) for r in rows], "total": total}


@router.post("/send", status_code=202)
def trigger_send(
    match_id: str,
    _user: OfficerUser,
    db: Session = Depends(get_db),
):
    """Officer manually triggers notification for a match (e.g., after confirmation)."""
    count = send_notification_for_match(match_id)
    return {"queued": count, "match_id": match_id}
