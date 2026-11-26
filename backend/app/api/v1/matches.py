"""
Match listing, confirmation, and cancellation endpoints.
  GET  /matches                      – role-scoped list
  POST /matches/{match_id}/confirm   – farmer or buyer (or officer) confirms pickup
  POST /matches/{match_id}/cancel    – farmer or buyer (or officer) cancels
"""
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.core.errors import api_error, forbidden, not_found
from app.schemas.match import Match
from app.services import queries

router = APIRouter(prefix="/matches", tags=["matches"])


def _check_match_ownership(conn, match_id: str, user: dict) -> dict:
    row = conn.execute(
        text("SELECT match_id, village_id, buyer_id, status FROM matches WHERE match_id = :id"),
        {"id": match_id},
    ).mappings().first()
    if row is None:
        raise not_found("match", "match_id")

    role = user.get("role")
    if role == "farmer" and row["village_id"] != user.get("village_id"):
        raise forbidden("Farmers can only modify matches for their own village.")
    if role == "buyer" and row["buyer_id"] != user.get("buyer_id"):
        raise forbidden("Buyers can only modify their own matches.")
    return dict(row)


@router.get("", response_model=List[Match])
def list_matches(
    _user: CurrentUser,
    status: Optional[str] = None,
    village_id: Optional[str] = None,
):
    role = _user.get("role")
    buyer_id = None

    if role == "farmer":
        own_village = _user.get("village_id")
        if village_id and village_id != own_village:
            raise forbidden("Farmers can only view matches for their own village.")
        village_id = own_village
    elif role == "buyer":
        buyer_id = _user.get("buyer_id")

    return queries.list_matches(
        status.upper() if status else None,
        village_id,
        buyer_id=buyer_id,
    )


@router.post("/{match_id}/confirm", response_model=Match)
def confirm_match(
    match_id: str,
    _user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Farmer, buyer, or officer confirms the proposed pickup."""
    with db.connection() as conn:
        match = _check_match_ownership(conn, match_id, _user)
        if match["status"] != "PROPOSED":
            raise api_error(409, "CANNOT_CONFIRM",
                            "Match is not in PROPOSED state.", "match_id")
        conn.execute(
            text("UPDATE matches SET status = 'CONFIRMED' WHERE match_id = :id"),
            {"id": match_id},
        )
        conn.commit()
    rows = queries.list_matches(match_id=match_id)
    return rows[0]


@router.post("/{match_id}/cancel", response_model=Match)
def cancel_match(
    match_id: str,
    _user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Farmer, buyer, or officer cancels a proposed/confirmed pickup."""
    with db.connection() as conn:
        match = _check_match_ownership(conn, match_id, _user)
        if match["status"] not in ("PROPOSED", "CONFIRMED"):
            raise api_error(409, "CANNOT_CANCEL",
                            "Match cannot be cancelled in its current state.", "match_id")
        conn.execute(
            text("UPDATE matches SET status = 'CANCELLED' WHERE match_id = :id"),
            {"id": match_id},
        )
        conn.commit()
    rows = queries.list_matches(match_id=match_id)
    return rows[0]
