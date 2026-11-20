"""
Configuration parameters and agronomic baselines for Residue Compass Part 4.
All parameters represent research-backed defaults for Indo-Gangetic Plains (Punjab/Haryana/Western UP)
and can be overridden dynamically per scenario or village.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass
class EconomicsConfig:
    """Configurable agronomic, machinery, and market assumptions."""
    # Fuel and logistics
    diesel_price_inr_per_litre: float = 90.0
    default_road_winding_factor: float = 1.28  # Proxy multiplier to convert Haversine straight-line to road distance
    default_transport_cost_per_tonne_km_inr: float = 5.50
    default_fixed_loading_cost_inr_per_tonne: float = 180.0
    default_baling_cost_inr_per_tonne: float = 750.0

    # In-situ mulching / management (KEEP option)
    # Fertilizer equivalent values per metric tonne of dry paddy straw
    # Based on PAU/ICAR agronomic averages:
    # ~6 kg Nitrogen, ~1.5 kg Phosphorus (P2O5), ~15 kg Potassium (K2O), ~1.2 kg Sulfur
    nitrogen_kg_per_tonne: float = 6.0
    phosphorus_kg_per_tonne: float = 1.5
    potassium_kg_per_tonne: float = 15.0
    sulfur_kg_per_tonne: float = 1.2

    # Subsidized fertilizer prices in India (approx INR per kg active nutrient)
    urea_n_price_inr_per_kg: float = 6.0       # Urea ~INR 266 / 45kg bag (46% N) -> ~INR 5.9/kg N
    dap_p_price_inr_per_kg: float = 29.5       # DAP ~INR 1350 / 50kg bag (46% P2O5, 18% N)
    mop_k_price_inr_per_kg: float = 34.0       # MOP ~INR 1700 / 50kg bag (60% K2O)
    sulfur_price_inr_per_kg: float = 15.0

    # Soil health, water retention, and microbial organic carbon value
    soil_organic_matter_benefit_inr_per_tonne: float = 350.0

    # Cost of in-situ incorporation (Super Seeder / Happy Seeder tractor pass + diesel + wear)
    insitu_management_cost_inr_per_tonne: float = 520.0

    # Animal Feed (FEED option)
    default_fodder_market_value_inr_per_tonne: float = 1800.0
    feed_preparation_and_urea_treatment_cost_inr_per_tonne: float = 480.0
    feed_local_handling_cost_inr_per_tonne: float = 150.0

    # Alternative disposal / Burning benchmark
    # Configured financial penalty or loss associated with open field burning (e.g. NGT fine risk + labor)
    burning_penalty_or_loss_inr_per_tonne: float = 250.0

    # Price recommendation margins
    recommended_price_low_margin_ratio: float = 1.05   # 5% above break-even
    recommended_price_high_margin_ratio: float = 1.25  # 25% above break-even

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EconomicsConfig":
        valid_keys = {f for f in cls.__dataclass_fields__}
        filtered = {k: float(v) if isinstance(v, (int, float)) else v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class MatchingConfig:
    """Configurable constraints and knobs for matching optimization."""
    max_search_radius_km: float = 75.0
    allow_partial_fulfillment: bool = True
    min_dispatch_tonnes: float = 5.0
    urgency_deadline_days_threshold: int = 5
    urgency_weight: float = 50.0  # Weight applied per day of urgency in greedy priority
    distance_cost_penalty_weight: float = 1.0
    default_road_winding_factor: float = 1.28

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MatchingConfig":
        valid_keys = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
