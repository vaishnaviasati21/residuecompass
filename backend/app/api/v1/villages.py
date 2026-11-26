"""Villages router – list and detail, with optional district filter."""
from typing import List, Optional

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser
from app.core.errors import not_found
from app.schemas.village import VillageSummary
from app.services import queries

router = APIRouter(tags=["villages"])


@router.get("/villages", response_model=List[VillageSummary])
def list_villages(
    district: Optional[str] = None,
    _user: dict = Depends(CurrentUser),
):
    # Farmers see only their own village
    if _user.get("role") == "farmer":
        vid = _user.get("village_id")
        all_v = queries.list_villages(district)
        return [v for v in all_v if v["village_id"] == vid]
    return queries.list_villages(district)


@router.get("/villages/{village_id}", response_model=VillageSummary)
def get_village(
    village_id: str,
    _user: dict = Depends(CurrentUser),
):
    v = queries.get_village(village_id)
    if v is None:
        raise not_found("village", "village_id")
    return v
