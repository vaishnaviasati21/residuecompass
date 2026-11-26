"""Burn events router – burn-events endpoint."""
from typing import List, Optional

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser
from app.schemas.burn import BurnEvent
from app.services import queries

router = APIRouter(tags=["burn-events"])


@router.get("/burn-events", response_model=List[BurnEvent])
def list_burn_events(
    village_id: Optional[str] = None,
    confidence: Optional[str] = None,
    _user: dict = Depends(CurrentUser),
):
    # Farmers scope to their own village automatically
    if _user.get("role") == "farmer":
        village_id = _user.get("village_id")
    return queries.list_burn_events(
        village_id,
        confidence.upper() if confidence else None,
    )
