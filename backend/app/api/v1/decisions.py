from fastapi import APIRouter
from app.core.errors import api_error
from app.schemas.decision import Decision
from app.services import queries

router = APIRouter()


@router.get("/villages/{village_id}/decision", response_model=Decision)
def get_decision(village_id: str):
    data = queries.get_decision(village_id)
    if data is None:
        raise api_error(404, "DECISION_NOT_FOUND",
                        "No decision available for this village.", "village_id")
    return data