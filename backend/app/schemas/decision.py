from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel


class OptionValue(BaseModel):
    gain: float
    cost: float
    net: float


class PerTonne(BaseModel):
    keep: OptionValue
    sell: OptionValue
    feed: OptionValue


class PriceRange(BaseModel):
    low: float
    high: float


class Assumptions(BaseModel):
    fertilizer_value_per_tonne: float
    baling_cost_per_tonne: float
    transport_cost_per_tonne_per_km: float
    distance_km: float
    diesel_price_per_litre: float


class DecisionConfidence(BaseModel):
    tag: Literal["LOW", "MEDIUM", "HIGH"]
    reasons: List[str]


class Decision(BaseModel):
    village_id: str
    per_tonne_inr: PerTonne
    best_option: Literal["keep", "sell", "feed"]
    break_even_price_per_tonne_inr: float
    price_range_inr: PriceRange
    assumptions: Assumptions
    confidence: DecisionConfidence
    generated_at: datetime
