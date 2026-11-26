from fastapi import APIRouter, HTTPException
from app.adapters.forecast import get_forecast_provider
from app.schemas.forecast import Forecast

router = APIRouter()


@router.get("/villages/{village_id}/forecast", response_model=Forecast)
def get_forecast(village_id: str):
    data = get_forecast_provider().get(village_id)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "VILLAGE_NOT_FOUND",
                              "message": "No village with this ID.",
                              "field": "village_id"}},
        )
    return data