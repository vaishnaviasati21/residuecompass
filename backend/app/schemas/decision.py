from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


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


class SimulateAssumptions(BaseModel):
    """
    Caller-supplied economics overrides for the what-if simulator.
    All fields are optional (omitted fields fall back to the village's saved assumptions).
    Bounds are enforced at the HTTP layer so invalid values return 422, not 500.
    """
    fertilizer_value_per_tonne: Optional[float] = Field(
        None, ge=0, le=5000,
        description="Market value of retained straw as fertiliser (₹/t, 0–5000)",
    )
    baling_cost_per_tonne: Optional[float] = Field(
        None, ge=0, le=2000,
        description="Cost to bale and collect straw (₹/t, 0–2000)",
    )
    transport_cost_per_tonne_per_km: Optional[float] = Field(
        None, ge=0, le=100,
        description="Logistics cost per tonne per km (₹/t/km, 0–100)",
    )
    distance_km: Optional[float] = Field(
        None, ge=0, le=500,
        description="Distance from field to buyer facility (km, 0–500)",
    )
    diesel_price_per_litre: Optional[float] = Field(
        None, ge=50, le=200,
        description="Current diesel price (₹/L, 50–200)",
    )


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
