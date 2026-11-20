"""
Stable, typed data contracts for Residue Compass Part 4.
All schemas are pure dataclasses with strict input validation, serialization helpers,
and clear docstrings. Fully compatible with standard Python and easily convertible to Pydantic.
"""

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Literal
from residue_compass_economics.exceptions import ValidationError


def parse_iso_date(value: str | date) -> date:
    """Helper to parse ISO date strings into date objects."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError as e:
            raise ValidationError(f"Invalid date format '{value}'. Expected YYYY-MM-DD.") from e
    raise ValidationError(f"Expected string or date, got {type(value).__name__}")


@dataclass
class VillageStrawForecast:
    """Village-level harvest forecast from Part 3 ML models or historical priors."""
    village_id: str
    harvest_date: str  # YYYY-MM-DD
    straw_tonnes_low: float
    straw_tonnes_expected: float
    straw_tonnes_high: float
    confidence: Literal["Low", "Medium", "High"]
    village_name: str = ""
    collection_deadline: Optional[str] = None  # YYYY-MM-DD (e.g., wheat sowing window cut-off)
    latitude: float = 0.0
    longitude: float = 0.0
    is_simulated: bool = True

    def __post_init__(self):
        if not self.village_id or not isinstance(self.village_id, str):
            raise ValidationError("village_id must be a non-empty string.", field="village_id")
        
        # Date parsing
        h_date = parse_iso_date(self.harvest_date)
        self.harvest_date = h_date.isoformat()

        if self.collection_deadline:
            d_date = parse_iso_date(self.collection_deadline)
            if d_date < h_date:
                raise ValidationError(
                    f"collection_deadline ({d_date}) cannot be before harvest_date ({h_date}).",
                    field="collection_deadline",
                )
            self.collection_deadline = d_date.isoformat()

        # Validate tonnage
        if self.straw_tonnes_low < 0 or self.straw_tonnes_expected < 0 or self.straw_tonnes_high < 0:
            raise ValidationError("Straw tonnage values must be non-negative.", field="straw_tonnes")
        
        if not (self.straw_tonnes_low <= self.straw_tonnes_expected <= self.straw_tonnes_high):
            raise ValidationError(
                f"Tonnage ordering violation: expected low ({self.straw_tonnes_low}) <= "
                f"expected ({self.straw_tonnes_expected}) <= high ({self.straw_tonnes_high}).",
                field="straw_tonnes",
            )
        
        if self.confidence not in ["Low", "Medium", "High"]:
            raise ValidationError(
                f"Invalid confidence '{self.confidence}'. Must be 'Low', 'Medium', or 'High'.",
                field="confidence",
            )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VillageStrawForecast":
        return cls(**data)


@dataclass
class VillageEconomicInput:
    """Local context and market offers for economic evaluation."""
    village_id: str
    offered_straw_price_inr_per_tonne: Optional[float] = None
    buyer_distance_km: Optional[float] = None
    local_fodder_value_inr_per_tonne: Optional[float] = None
    custom_baling_cost_inr_per_tonne: Optional[float] = None
    custom_insitu_cost_inr_per_tonne: Optional[float] = None
    buyer_covers_transport: bool = False
    buyer_covers_baling: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VillageEconomicInput":
        return cls(**data)


@dataclass
class EconomicDecision:
    """Comparative economic evaluation of KEEP vs SELL vs FEED."""
    village_id: str
    best_choice: Literal["keep", "sell", "feed"]
    break_even_price_inr_per_tonne: float
    recommended_price_low_inr_per_tonne: float
    recommended_price_high_inr_per_tonne: float
    net_keep_value_inr_per_tonne: float
    net_sell_value_inr_per_tonne: float
    net_feed_value_inr_per_tonne: float
    currency: str = "INR"
    assumptions: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    is_simulated: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EconomicDecision":
        return cls(**data)


@dataclass
class Buyer:
    """Biomass aggregators, paper mills, briquette/pellet plants, or power utilities."""
    buyer_id: str
    name: str
    latitude: float
    longitude: float
    max_demand_tonnes: float
    remaining_demand_tonnes: float
    offered_price_inr_per_tonne: float
    valid_from: str  # YYYY-MM-DD
    valid_until: str  # YYYY-MM-DD
    location_id: Optional[str] = None
    covers_transport: bool = False
    covers_baling: bool = False
    is_simulated: bool = True

    def __post_init__(self):
        if not self.buyer_id:
            raise ValidationError("buyer_id cannot be empty.", field="buyer_id")
        if self.max_demand_tonnes <= 0:
            raise ValidationError("max_demand_tonnes must be greater than zero.", field="max_demand_tonnes")
        if self.remaining_demand_tonnes < 0:
            raise ValidationError("remaining_demand_tonnes cannot be negative.", field="remaining_demand_tonnes")
        if self.offered_price_inr_per_tonne <= 0:
            raise ValidationError("offered_price_inr_per_tonne must be greater than zero.", field="offered_price")
        
        vf = parse_iso_date(self.valid_from)
        vu = parse_iso_date(self.valid_until)
        if vu < vf:
            raise ValidationError("Buyer valid_until cannot be before valid_from.", field="valid_until")
        self.valid_from = vf.isoformat()
        self.valid_until = vu.isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Buyer":
        return cls(**data)


@dataclass
class Baler:
    """Agricultural equipment unit for compressing loose straw into dense bales."""
    baler_id: str
    owner_name: str
    latitude: float
    longitude: float
    daily_capacity_tonnes: float
    cost_per_tonne_inr: float
    available_from: str  # YYYY-MM-DD
    available_until: str  # YYYY-MM-DD
    location_name: str = ""
    is_operational: bool = True
    is_simulated: bool = True

    def __post_init__(self):
        if not self.baler_id:
            raise ValidationError("baler_id cannot be empty.", field="baler_id")
        if self.daily_capacity_tonnes <= 0:
            raise ValidationError("daily_capacity_tonnes must be > 0.", field="daily_capacity_tonnes")
        if self.cost_per_tonne_inr <= 0:
            raise ValidationError("cost_per_tonne_inr must be > 0.", field="cost_per_tonne_inr")
        
        af = parse_iso_date(self.available_from)
        au = parse_iso_date(self.available_until)
        if au < af:
            raise ValidationError("Baler available_until cannot be before available_from.", field="available_until")
        self.available_from = af.isoformat()
        self.available_until = au.isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Baler":
        return cls(**data)


@dataclass
class Truck:
    """Transport logistics resource (tractor-trolley or flatbed truck)."""
    truck_id: str
    transporter_name: str
    latitude: float
    longitude: float
    daily_capacity_tonnes: float
    cost_per_tonne_km_inr: float
    fixed_base_cost_inr: float
    available_from: str  # YYYY-MM-DD
    available_until: str  # YYYY-MM-DD
    location_name: str = ""
    is_operational: bool = True
    is_simulated: bool = True

    def __post_init__(self):
        if not self.truck_id:
            raise ValidationError("truck_id cannot be empty.", field="truck_id")
        if self.daily_capacity_tonnes <= 0:
            raise ValidationError("daily_capacity_tonnes must be > 0.", field="daily_capacity_tonnes")
        if self.cost_per_tonne_km_inr < 0:
            raise ValidationError("cost_per_tonne_km_inr cannot be negative.", field="cost_per_tonne_km_inr")
        if self.fixed_base_cost_inr < 0:
            raise ValidationError("fixed_base_cost_inr cannot be negative.", field="fixed_base_cost_inr")
        
        af = parse_iso_date(self.available_from)
        au = parse_iso_date(self.available_until)
        if au < af:
            raise ValidationError("Truck available_until cannot be before available_from.", field="available_until")
        self.available_from = af.isoformat()
        self.available_until = au.isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Truck":
        return cls(**data)


@dataclass
class MatchBooking:
    """A feasible operational dispatch booking tying village, buyer, baler, and truck."""
    match_id: str
    village_id: str
    buyer_id: str
    baler_id: str
    truck_id: str
    pickup_date: str  # YYYY-MM-DD
    matched_tonnes: float
    price_inr_per_tonne: float
    transport_distance_km: float
    transport_cost_inr: float
    baling_cost_inr: float
    loading_cost_inr: float
    total_cost_inr: float
    estimated_farmer_net_revenue_inr: float
    estimated_saving_vs_burning_inr: float
    estimated_tonnes_diverted: float
    status: Literal["CONFIRMED", "PROPOSED", "CANCELLED"] = "CONFIRMED"
    is_simulated: bool = True
    assumptions: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""

    def __post_init__(self):
        if not self.match_id:
            raise ValidationError("match_id cannot be empty.")
        if self.matched_tonnes <= 0:
            raise ValidationError("matched_tonnes must be > 0.")
        p_date = parse_iso_date(self.pickup_date)
        self.pickup_date = p_date.isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MatchBooking":
        return cls(**data)


@dataclass
class UnmatchedVillage:
    """Detailed record of unmatched or partially matched village supply."""
    village_id: str
    forecast_tonnes: float
    remaining_unmatched_tonnes: float
    reason: str


@dataclass
class UnfilledBuyerDemand:
    """Detailed record of unfulfilled buyer orders."""
    buyer_id: str
    buyer_name: str
    initial_demand_tonnes: float
    remaining_demand_tonnes: float
    reason: str


@dataclass
class MatchingResult:
    """Comprehensive output of the matching engine."""
    bookings: List[MatchBooking]
    unmatched_villages: List[UnmatchedVillage]
    unfilled_buyers: List[UnfilledBuyerDemand]
    unscheduled_balers: List[str]
    unscheduled_trucks: List[str]
    total_forecast_tonnes: float
    total_matched_tonnes: float
    total_unmatched_tonnes: float
    total_farmer_net_revenue_inr: float
    total_estimated_tonnes_diverted: float
    warnings: List[str] = field(default_factory=list)
    is_simulated: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MatchingResult":
        bookings = [MatchBooking.from_dict(b) if isinstance(b, dict) else b for b in data.get("bookings", [])]
        unmatched_villages = [UnmatchedVillage(**u) if isinstance(u, dict) else u for u in data.get("unmatched_villages", [])]
        unfilled_buyers = [UnfilledBuyerDemand(**b) if isinstance(b, dict) else b for b in data.get("unfilled_buyers", [])]
        
        return cls(
            bookings=bookings,
            unmatched_villages=unmatched_villages,
            unfilled_buyers=unfilled_buyers,
            unscheduled_balers=data.get("unscheduled_balers", []),
            unscheduled_trucks=data.get("unscheduled_trucks", []),
            total_forecast_tonnes=data.get("total_forecast_tonnes", 0.0),
            total_matched_tonnes=data.get("total_matched_tonnes", 0.0),
            total_unmatched_tonnes=data.get("total_unmatched_tonnes", 0.0),
            total_farmer_net_revenue_inr=data.get("total_farmer_net_revenue_inr", 0.0),
            total_estimated_tonnes_diverted=data.get("total_estimated_tonnes_diverted", 0.0),
            warnings=data.get("warnings", []),
            is_simulated=data.get("is_simulated", True),
        )


@dataclass
class ImpactSummary:
    """Environmental and financial impact metrics."""
    total_forecast_straw_tonnes: float
    total_matched_tonnes: float
    total_unmatched_tonnes: float
    matched_fraction: float
    estimated_tonnes_diverted: float
    estimated_farmer_net_revenue_inr: float
    estimated_farmer_savings_vs_burning_inr: float
    assumptions_summary: Dict[str, Any]
    confidence_and_limitations: str
    is_simulated: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImpactSummary":
        return cls(**data)


@dataclass
class StressScenario:
    """Definition of an economic or logistics stress test scenario."""
    scenario_id: str
    name: str
    description: str
    overrides: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioOutcome:
    """Result of running a single stress scenario."""
    scenario_id: str
    name: str
    baseline_choice: str
    scenario_choice: str
    choice_changed: bool
    baseline_break_even_price: float
    scenario_break_even_price: float
    delta_break_even_price: float
    root_cause_explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StressTestReport:
    """Aggregated stress testing report across multiple scenarios."""
    village_id: str
    baseline_decision: EconomicDecision
    outcomes: List[ScenarioOutcome]
    summary_insight: str
    is_simulated: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WhatIfResult:
    """Result of recalculating decisions under custom what-if overrides."""
    village_id: str
    baseline_decision: EconomicDecision
    updated_decision: EconomicDecision
    applied_overrides: Dict[str, Any]
    changed_fields: Dict[str, Any]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    """Result of project data consistency and constraint checking."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
