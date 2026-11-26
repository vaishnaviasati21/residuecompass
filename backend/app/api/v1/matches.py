from typing import List, Optional
from fastapi import APIRouter
from app.schemas.match import Match
from app.services import queries

router = APIRouter()


@router.get("/matches", response_model=List[Match])
def list_matches(status: Optional[str] = None, village_id: Optional[str] = None):
    return queries.list_matches(status.upper() if status else None, village_id)