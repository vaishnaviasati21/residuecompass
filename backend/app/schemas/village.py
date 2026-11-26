from datetime import date
from typing import Literal
from pydantic import BaseModel
from app.schemas.common import ConfidenceTag, Point


class VillageSummary(BaseModel):
    village_id: str
    village_name: str
    district: str
    centroid: Point
    paddy_area_ha: float
    harvest_status: Literal["GROWING", "READY_SOON", "HARVESTED"]
    expected_harvest_date: date
    expected_straw_tonnes: float
    confidence: ConfidenceTag
