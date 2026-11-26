from fastapi import APIRouter
from app.core.errors import api_error
from app.schemas.forecast import Forecast
from app.services import queries

router = APIRouter()


@router.get("/villages/{village_id}/forecast", response_model=Forecast)
def get_forecast(village_id: str):
    data = queries.get_forecast(village_id)
    if data is None:
        raise api_error(404, "FORECAST_NOT_FOUND",
                        "No forecast available for this village.", "village_id")
    return data