"""
Forecasts router – villages/{village_id}/forecast.
Farmers can only view their own village; officers can view any.
"""
from fastapi import APIRouter, Depends

from app.core.deps import FarmerUser
from app.core.errors import forbidden, not_found
from app.schemas.forecast import Forecast
from app.services import queries

router = APIRouter(tags=["forecast"])


@router.get("/villages/{village_id}/forecast", response_model=Forecast)
def get_forecast(
    village_id: str,
    _user: dict = Depends(FarmerUser),
):
    if _user.get("role") == "farmer" and _user.get("village_id") != village_id:
        raise forbidden()
    data = queries.get_forecast(village_id)
    if data is None:
        raise not_found("forecast", "village_id")
    return data
