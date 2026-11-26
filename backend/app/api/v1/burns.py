"""Burn events router – burn-events endpoint."""
from typing import List, Optional

from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.core.errors import forbidden
from app.schemas.burn import BurnEvent
from app.services import queries

router = APIRouter(tags=["burn-events"])


@router.get("/burn-events", response_model=List[BurnEvent])
def list_burn_events(
    _user: CurrentUser,
    village_id: Optional[str] = None,
    confidence: Optional[str] = None,
):
    # Farmers scope to their own village automatically
    if _user.get("role") == "farmer":
        own_village = _user.get("village_id")
        if village_id and village_id != own_village:
            raise forbidden("Farmers can only view burn events for their own village.")
        village_id = own_village
    return queries.list_burn_events(
        village_id,
        confidence.upper() if confidence else None,
    )
