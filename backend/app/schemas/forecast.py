from datetime import date, datetime
from typing import List, Literal
from pydantic import BaseModel


class Harvest(BaseModel):
    expected_date: date
    earliest_date: date
    latest_date: date


class Straw(BaseModel):
    paddy_area_ha: float
    expected_tonnes: float
    low_tonnes: float
    high_tonnes: float


class Confidence(BaseModel):
    tag: Literal["LOW", "MEDIUM", "HIGH"]
    reasons: List[str]


class Forecast(BaseModel):
    village_id: str
    village_name: str
    district: str
    season: str
    harvest: Harvest
    straw: Straw
    confidence: Confidence
    model_version: str
    generated_at: datetime