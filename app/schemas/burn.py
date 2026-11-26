from datetime import date
from pydantic import BaseModel
from app.schemas.common import ConfidenceTag, Point


class Evidence(BaseModel):
    fire_points: int
    burn_scar_detected: bool
    burn_area_ha: float


class BurnEvent(BaseModel):
    event_id: str
    village_id: str
    location: Point
    detected_on: date
    confidence: ConfidenceTag
    evidence: Evidence
    source: str
