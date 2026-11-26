from typing import List, Optional
from fastapi import APIRouter
from app.schemas.burn import BurnEvent
from app.services import queries

router = APIRouter()


@router.get("/burn-events", response_model=List[BurnEvent])
def list_burn_events(village_id: Optional[str] = None, confidence: Optional[str] = None):
    return queries.list_burn_events(village_id, confidence.upper() if confidence else None)