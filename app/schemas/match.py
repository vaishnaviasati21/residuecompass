from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel


class BuyerRef(BaseModel):
    id: str
    name: str
    type: Literal["POWER", "PELLET", "BIOGAS", "OTHER"]
    distance_km: float


class IdRef(BaseModel):
    id: str


class Match(BaseModel):
    match_id: str
    village_id: str
    status: Literal["PROPOSED", "CONFIRMED", "COMPLETED", "CANCELLED"]
    tonnes: float
    buyer: BuyerRef
    baler: IdRef
    truck: IdRef
    pickup_date: date
    price_per_tonne_inr: float
    net_to_farmers_inr: float
    saving_vs_burning_note: str
    created_at: datetime
