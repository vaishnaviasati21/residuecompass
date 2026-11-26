"""
Match confirmation endpoint added to the existing matches list.
  POST /matches/{match_id}/confirm   – farmer or buyer confirms pickup
  POST /matches/{match_id}/cancel    – officer or farmer cancels
"""
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import BuyerUser, CurrentUser, FarmerUser, OfficerUser
from app.core.errors import api_error, not_found
from app.schemas.match import Match
from app.services import queries

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=List[Match])
def list_matches(
    status: Optional[str] = None,
    village_id: Optional[str] = None,
    _user: dict = Depends(CurrentUser),
    db: Session = Depends(get_db),
):
    # Farmers see only their village; buyers see only their buyer_id; officers see all
    role = _user.get("role")
    if role == "farmer":
        village_id = village_id or _user.get("village_id")
    elif role == "buyer":
        buyer_id = _user.get("buyer_id")
        return queries.list_matches(
            status.upper() if status else None,
            village_id,
            buyer_id=buyer_id,
        )
    return queries.list_matches(
        status.upper() if status else None,
        village_id,
    )


@router.post("/{match_id}/confirm", response_model=Match)
def confirm_match(
    match_id: str,
    _user: dict = Depends(FarmerUser),
    db: Session = Depends(get_db),
):
    """Farmer or buyer confirms the proposed pickup."""
    with db.connection() as conn:
        r = conn.execute(
            text("""
                UPDATE matches SET status = 'CONFIRMED'
                WHERE match_id = :id AND status = 'PROPOSED'
                RETURNING match_id
            """),
            {"id": match_id},
        ).first()
        conn.commit()
    if r is None:
        raise api_error(409, "CANNOT_CONFIRM",
                        "Match not found or not in PROPOSED state.", "match_id")
    rows = queries.list_matches(village_id=None, status=None, match_id=match_id)
    return rows[0]


@router.post("/{match_id}/cancel", response_model=Match)
def cancel_match(
    match_id: str,
    _user: dict = Depends(FarmerUser),
    db: Session = Depends(get_db),
):
    with db.connection() as conn:
        r = conn.execute(
            text("""
                UPDATE matches SET status = 'CANCELLED'
                WHERE match_id = :id AND status IN ('PROPOSED','CONFIRMED')
                RETURNING match_id
            """),
            {"id": match_id},
        ).first()
        conn.commit()
    if r is None:
        raise not_found("match", "match_id")
    rows = queries.list_matches(village_id=None, status=None, match_id=match_id)
    return rows[0]
