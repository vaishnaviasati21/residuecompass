"""
Match listing, confirmation, and cancellation endpoints.
  GET  /matches                      – role-scoped list
  POST /matches/{match_id}/confirm   – farmer, buyer, or officer confirms pickup
  POST /matches/{match_id}/cancel    – farmer, buyer, or officer cancels

Ownership and status guards are enforced with a **single atomic UPDATE**
(no read-then-write race).  The WHERE clause checks ownership + current status
in one SQL statement; zero rows returned means either not-found, wrong-owner,
or wrong-status – a follow-up read distinguishes these cases for the error message.
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
from app.services.audit import log_action

router = APIRouter(prefix="/matches", tags=["matches"])


def _ownership_clause(user: dict) -> tuple[str, dict]:
    """
    Return the SQL fragment and params that restrict a match to the caller's scope.
    Officer: unrestricted.  Farmer: own village.  Buyer: own buyer row.
    """
    role = user.get("role")
    if role == "officer":
        return "1=1", {}
    if role == "farmer":
        return "village_id = :caller_village", {"caller_village": user.get("village_id")}
    if role == "buyer":
        return "buyer_id = :caller_buyer", {"caller_buyer": user.get("buyer_id")}
    return "1=0", {}   # deny-by-default for unknown roles


def _atomic_transition(
    conn,
    match_id: str,
    new_status: str,
    allowed_from: tuple[str, ...],
    user: dict,
) -> Optional[dict]:
    """
    Attempt to transition a match's status in a single atomic UPDATE.

    WHERE clause enforces:
      1. correct match_id
      2. current status is in allowed_from
      3. caller owns the match (farmer-village / buyer-id / officer=all)

    Returns the updated row mapping if successful, None if 0 rows matched.
    """
    ownership_sql, ownership_params = _ownership_clause(user)
    statuses_placeholder = ", ".join(f"'{s}'" for s in allowed_from)

    result = conn.execute(
        text(f"""
            UPDATE matches
               SET status = :new_status
             WHERE match_id = :mid
               AND status IN ({statuses_placeholder})
               AND ({ownership_sql})
            RETURNING match_id, village_id, buyer_id, status
        """),
        {"new_status": new_status, "mid": match_id, **ownership_params},
    ).mappings().first()
    return dict(result) if result else None


def _diagnose_failed_transition(conn, match_id: str, user: dict) -> None:
    """
    After a failed atomic transition, raise the most informative error.
    Checks existence, then ownership, then emits a 409 for wrong-status.
    """
    row = conn.execute(
        text("SELECT village_id, buyer_id, status FROM matches WHERE match_id = :id"),
        {"id": match_id},
    ).mappings().first()

    if row is None:
        raise not_found("match", "match_id")

    role = user.get("role")
    if role == "farmer" and row["village_id"] != user.get("village_id"):
        raise forbidden("Farmers can only modify matches for their own village.")
    if role == "buyer" and row["buyer_id"] != user.get("buyer_id"):
        raise forbidden("Buyers can only modify their own matches.")

    raise api_error(
        409, "WRONG_STATUS",
        f"Match is in '{row['status']}' – transition not allowed from this state.",
        "match_id",
    )


@router.get("", response_model=List[Match])
def list_matches(
    _user: CurrentUser,
    status: Optional[str] = None,
    village_id: Optional[str] = None,
):
    """List matches, scoped by the caller's role."""
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
    """
    Farmer, buyer, or officer atomically confirms a PROPOSED match.
    Raises 404 / 403 / 409 if the guard fails.
    """
    with db.connection() as conn:
        updated = _atomic_transition(
            conn, match_id, "CONFIRMED", ("PROPOSED",), _user
        )
        if updated is None:
            _diagnose_failed_transition(conn, match_id, _user)
        conn.commit()

    log_action(
        user_id=int(_user.get("sub", 0)),
        action="match_confirmed",
        entity="match",
        entity_id=match_id,
        details={"by_role": _user.get("role")},
    )
    rows = queries.list_matches(match_id=match_id)
    return rows[0]


@router.post("/{match_id}/cancel", response_model=Match)
def cancel_match(
    match_id: str,
    _user: CurrentUser,
    db: Session = Depends(get_db),
):
    """
    Farmer, buyer, or officer atomically cancels a PROPOSED or CONFIRMED match.
    Raises 404 / 403 / 409 if the guard fails.
    """
    with db.connection() as conn:
        updated = _atomic_transition(
            conn, match_id, "CANCELLED", ("PROPOSED", "CONFIRMED"), _user
        )
        if updated is None:
            _diagnose_failed_transition(conn, match_id, _user)
        conn.commit()

    log_action(
        user_id=int(_user.get("sub", 0)),
        action="match_cancelled",
        entity="match",
        entity_id=match_id,
        details={"by_role": _user.get("role")},
    )
    rows = queries.list_matches(match_id=match_id)
    return rows[0]
