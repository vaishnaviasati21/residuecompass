"""Buyer registry shapes."""
from typing import Literal
from pydantic import BaseModel
from app.schemas.common import Point


class Buyer(BaseModel):
    id: str
    name: str
    type: Literal["POWER", "PELLET", "BIOGAS", "OTHER"]
    location: Point
    capacity_t_per_day: float
    price_per_tonne_inr: float
    active: bool


class BuyerList(BaseModel):
    items: list[Buyer]
    total: int
