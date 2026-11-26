"""
Buyers registry.
  GET /buyers           – list all buyers (officer + farmer read)
  GET /buyers/{id}      – detail for one buyer
  PATCH /buyers/{id}    – update price / capacity  (officer only)
"""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import FarmerUser, OfficerUser
from app.core.errors import not_found
from app.schemas.buyer import Buyer

router = APIRouter(prefix="/buyers", tags=["buyers"])


def _row_to_buyer(r) -> dict:
    return {
        "id": r["id"],
        "name": r["name"],
        "type": r["type"],
        "location": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
        "capacity_t_per_day": r["capacity_t_per_day"],
        "price_per_tonne_inr": r["price_per_tonne_inr"],
        "active": r["active"],
    }


@router.get("", response_model=list[Buyer])
def list_buyers(
    _user: FarmerUser,
    buyer_type: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    sql = text("""
        SELECT id, name, type, capacity_t_per_day, price_per_tonne_inr, active,
               ST_X(geom) AS lon, ST_Y(geom) AS lat
        FROM buyers
        WHERE (:active_only IS FALSE OR active = TRUE)
          AND (CAST(:type AS text) IS NULL OR type = CAST(:type AS text))
        ORDER BY name
    """)
    with db.connection() as conn:
        rows = conn.execute(sql, {
            "active_only": active_only,
            "type": buyer_type.upper() if buyer_type else None,
        }).mappings().all()
    return [_row_to_buyer(r) for r in rows]


@router.get("/{buyer_id}", response_model=Buyer)
def get_buyer(
    buyer_id: str,
    _user: FarmerUser,
    db: Session = Depends(get_db),
):
    sql = text("""
        SELECT id, name, type, capacity_t_per_day, price_per_tonne_inr, active,
               ST_X(geom) AS lon, ST_Y(geom) AS lat
        FROM buyers WHERE id = :id
    """)
    with db.connection() as conn:
        r = conn.execute(sql, {"id": buyer_id}).mappings().first()
    if r is None:
        raise not_found("buyer", "buyer_id")
    return _row_to_buyer(r)


@router.patch("/{buyer_id}", response_model=Buyer)
def update_buyer(
    buyer_id: str,
    _user: OfficerUser,
    price_per_tonne_inr: Optional[float] = None,
    capacity_t_per_day: Optional[float] = None,
    active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """Officer-only: adjust pricing / availability."""
    updates = {}
    if price_per_tonne_inr is not None:
        updates["price_per_tonne_inr"] = price_per_tonne_inr
    if capacity_t_per_day is not None:
        updates["capacity_t_per_day"] = capacity_t_per_day
    if active is not None:
        updates["active"] = active
    if not updates:
        raise not_found("buyer", "buyer_id")   # triggers caller to supply something

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = buyer_id
    with db.connection() as conn:
        r = conn.execute(
            text(f"UPDATE buyers SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        ).mappings().first()
        conn.commit()
    if r is None:
        raise not_found("buyer", "buyer_id")
    return _row_to_buyer(r)
