"""
Synthetic benchmark datasets representing authentic agricultural scenarios in Punjab and Haryana.
All entities are clearly marked with `is_simulated: True`.
Includes 4 villages, 3 buyers, 3 balers, and 4 trucks.
"""

from typing import List, Dict, Any
from residue_compass_economics.schemas import (
    VillageStrawForecast,
    VillageEconomicInput,
    Buyer,
    Baler,
    Truck,
)


def get_sample_forecasts() -> List[VillageStrawForecast]:
    """
    Returns 4 synthetic village harvest forecasts:
    - VIL-001 (Raikot, Ludhiana): High expected yield, near industrial buyers, short window.
    - VIL-002 (Bhawanigarh, Sangrur): Medium yield, high local livestock density (good feed candidate).
    - VIL-003 (Samana, Patiala): High yield, distant buyers (transport cost test case).
    - VIL-004 (Nilokheri, Karnal): Tight harvest deadline, testing capacity constraints and partial matching.
    """
    return [
        VillageStrawForecast(
            village_id="VIL-001",
            village_name="Raikot Cluster",
            harvest_date="2026-10-20",
            collection_deadline="2026-11-04",
            straw_tonnes_low=140.0,
            straw_tonnes_expected=160.0,
            straw_tonnes_high=185.0,
            confidence="High",
            latitude=30.6500,
            longitude=75.6000,
            is_simulated=True,
        ),
        VillageStrawForecast(
            village_id="VIL-002",
            village_name="Bhawanigarh Dairy Belt",
            harvest_date="2026-10-22",
            collection_deadline="2026-11-06",
            straw_tonnes_low=85.0,
            straw_tonnes_expected=100.0,
            straw_tonnes_high=115.0,
            confidence="Medium",
            latitude=30.2700,
            longitude=76.0400,
            is_simulated=True,
        ),
        VillageStrawForecast(
            village_id="VIL-003",
            village_name="Samana Remote Farms",
            harvest_date="2026-10-24",
            collection_deadline="2026-11-08",
            straw_tonnes_low=190.0,
            straw_tonnes_expected=220.0,
            straw_tonnes_high=250.0,
            confidence="High",
            latitude=30.1500,
            longitude=76.1900,
            is_simulated=True,
        ),
        VillageStrawForecast(
            village_id="VIL-004",
            village_name="Nilokheri Urgent Zone",
            harvest_date="2026-10-21",
            collection_deadline="2026-10-28",  # Strict 7-day sowing window
            straw_tonnes_low=110.0,
            straw_tonnes_expected=130.0,
            straw_tonnes_high=145.0,
            confidence="Medium",
            latitude=29.8300,
            longitude=76.9200,
            is_simulated=True,
        ),
    ]


def get_sample_economic_inputs() -> Dict[str, VillageEconomicInput]:
    """
    Returns tailored economic input baselines:
    - VIL-001: High competitive buyer offer (INR 2,250/t), nearby plant (12km) -> Clear SELL.
    - VIL-002: Strong local cattle feed market (INR 2,400/t) -> Clear FEED.
    - VIL-003: Low buyer offer (INR 1,200/t) and long distance (55km) -> Clear KEEP.
    - VIL-004: Moderate offer (INR 1,950/t), 25km -> SELL competitive.
    """
    return {
        "VIL-001": VillageEconomicInput(
            village_id="VIL-001",
            offered_straw_price_inr_per_tonne=2250.0,
            buyer_distance_km=12.0,
            local_fodder_value_inr_per_tonne=1500.0,
            buyer_covers_transport=False,
            buyer_covers_baling=False,
        ),
        "VIL-002": VillageEconomicInput(
            village_id="VIL-002",
            offered_straw_price_inr_per_tonne=1600.0,
            buyer_distance_km=28.0,
            local_fodder_value_inr_per_tonne=2400.0,  # High local dairy fodder value
            buyer_covers_transport=False,
            buyer_covers_baling=False,
        ),
        "VIL-003": VillageEconomicInput(
            village_id="VIL-003",
            offered_straw_price_inr_per_tonne=1200.0,  # Below break-even
            buyer_distance_km=55.0,
            local_fodder_value_inr_per_tonne=950.0,    # Low local cattle fodder demand -> Net Feed = 320 < Net Keep = 438.25
            buyer_covers_transport=False,
            buyer_covers_baling=False,
        ),
        "VIL-004": VillageEconomicInput(
            village_id="VIL-004",
            offered_straw_price_inr_per_tonne=1950.0,
            buyer_distance_km=25.0,
            local_fodder_value_inr_per_tonne=1600.0,
            buyer_covers_transport=False,
            buyer_covers_baling=False,
        ),
    }


def get_sample_buyers() -> List[Buyer]:
    """
    Returns 3 synthetic buyers:
    - BUY-001: Malwa Biomass Power Ltd (Ludhiana) - high demand (250t), competitive price (INR 2,250/t).
    - BUY-002: GreenFuel Compressed Biogas (Sangrur) - medium demand (150t), covers baling! (INR 1,850/t).
    - BUY-003: Shreyans Paper & Board Mill (Ahmedgarh) - moderate demand (100t), price (INR 2,100/t).
    """
    return [
        Buyer(
            buyer_id="BUY-001",
            name="Malwa Biomass Power Plant",
            latitude=30.6800,
            longitude=75.6400,
            max_demand_tonnes=250.0,
            remaining_demand_tonnes=250.0,
            offered_price_inr_per_tonne=2250.0,
            valid_from="2026-10-15",
            valid_until="2026-11-20",
            location_id="LOC-LUDHIANA-IND",
            covers_transport=False,
            covers_baling=False,
            is_simulated=True,
        ),
        Buyer(
            buyer_id="BUY-002",
            name="GreenFuel CBG Bio-Energy",
            latitude=30.2500,
            longitude=75.9800,
            max_demand_tonnes=150.0,
            remaining_demand_tonnes=150.0,
            offered_price_inr_per_tonne=1850.0,
            valid_from="2026-10-18",
            valid_until="2026-11-15",
            location_id="LOC-SANGRUR-CBG",
            covers_transport=False,
            covers_baling=True,  # Incentive: buyer absorbs baling costs
            is_simulated=True,
        ),
        Buyer(
            buyer_id="BUY-003",
            name="Shreyans Paper & Board Mills",
            latitude=30.6200,
            longitude=75.8200,
            max_demand_tonnes=100.0,
            remaining_demand_tonnes=100.0,
            offered_price_inr_per_tonne=2100.0,
            valid_from="2026-10-20",
            valid_until="2026-11-10",
            location_id="LOC-AHMEDGARH-IND",
            covers_transport=False,
            covers_baling=False,
            is_simulated=True,
        ),
    ]


def get_sample_balers() -> List[Baler]:
    """Returns 3 balers operating in the region."""
    return [
        Baler(
            baler_id="BAL-001",
            owner_name="Gurmeet Custom Hiring Centre",
            latitude=30.6300,
            longitude=75.6200,
            daily_capacity_tonnes=60.0,
            cost_per_tonne_inr=720.0,
            available_from="2026-10-18",
            available_until="2026-11-15",
            location_name="Raikot Hub",
            is_operational=True,
            is_simulated=True,
        ),
        Baler(
            baler_id="BAL-002",
            owner_name="Kisan Agro Machinery Co-op",
            latitude=30.2800,
            longitude=76.0100,
            daily_capacity_tonnes=50.0,
            cost_per_tonne_inr=750.0,
            available_from="2026-10-20",
            available_until="2026-11-12",
            location_name="Bhawanigarh Hub",
            is_operational=True,
            is_simulated=True,
        ),
        Baler(
            baler_id="BAL-003",
            owner_name="Doaba Modern Balers",
            latitude=29.8500,
            longitude=76.9000,
            daily_capacity_tonnes=45.0,
            cost_per_tonne_inr=760.0,
            available_from="2026-10-19",
            available_until="2026-11-10",
            location_name="Karnal North",
            is_operational=True,
            is_simulated=True,
        ),
    ]


def get_sample_trucks() -> List[Truck]:
    """Returns 4 trucks/trolleys operating in the logistics network."""
    return [
        Truck(
            truck_id="TRK-001",
            transporter_name="Sher-e-Punjab Logistics 16T",
            latitude=30.6400,
            longitude=75.6100,
            daily_capacity_tonnes=45.0,
            cost_per_tonne_km_inr=5.20,
            fixed_base_cost_inr=1500.0,
            available_from="2026-10-18",
            available_until="2026-11-20",
            location_name="Ludhiana South",
            is_operational=True,
            is_simulated=True,
        ),
        Truck(
            truck_id="TRK-002",
            transporter_name="Malwa Heavy Haulage 20T",
            latitude=30.6700,
            longitude=75.6500,
            daily_capacity_tonnes=55.0,
            cost_per_tonne_km_inr=5.00,
            fixed_base_cost_inr=1800.0,
            available_from="2026-10-19",
            available_until="2026-11-18",
            location_name="Ludhiana Bypass",
            is_operational=True,
            is_simulated=True,
        ),
        Truck(
            truck_id="TRK-003",
            transporter_name="Sangrur Rural Trolleys 10T",
            latitude=30.2600,
            longitude=76.0200,
            daily_capacity_tonnes=30.0,
            cost_per_tonne_km_inr=5.60,
            fixed_base_cost_inr=900.0,
            available_from="2026-10-20",
            available_until="2026-11-14",
            location_name="Bhawanigarh Stand",
            is_operational=True,
            is_simulated=True,
        ),
        Truck(
            truck_id="TRK-004",
            transporter_name="GT Road Express Transport 14T",
            latitude=29.8400,
            longitude=76.9100,
            daily_capacity_tonnes=40.0,
            cost_per_tonne_km_inr=5.40,
            fixed_base_cost_inr=1200.0,
            available_from="2026-10-19",
            available_until="2026-11-15",
            location_name="Nilokheri Highway",
            is_operational=True,
            is_simulated=True,
        ),
    ]
