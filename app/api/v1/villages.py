from typing import List, Optional
from fastapi import APIRouter
from app.core.errors import api_error
from app.schemas.village import VillageSummary
from app.services import queries

router = APIRouter()


@router.get("/villages", response_model=List[VillageSummary])
def list_villages(district: Optional[str] = None):
    return queries.list_villages(district)


@router.get("/villages/{village_id}", response_model=VillageSummary)
def get_village(village_id: str):
    v = queries.get_village(village_id)
    if v is None:
        raise api_error(404, "VILLAGE_NOT_FOUND", "No village with this ID.", "village_id")
    return v