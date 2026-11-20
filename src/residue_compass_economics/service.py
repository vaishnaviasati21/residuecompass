"""
Public Service Boundary for Residue Compass Part 4.
This module exposes the official, stable Python API imported by Part 1 (Backend).
"""

from typing import List, Dict, Any, Optional
from residue_compass_economics.config import EconomicsConfig, MatchingConfig
from residue_compass_economics.schemas import (
    VillageStrawForecast,
    VillageEconomicInput,
    EconomicDecision,
    Buyer,
    Baler,
    Truck,
    MatchBooking,
    MatchingResult,
    ImpactSummary,
    StressScenario,
    StressTestReport,
    WhatIfResult,
    ValidationResult,
)
from residue_compass_economics.economics import (
    evaluate_village_economics,
    execute_what_if_analysis,
)
from residue_compass_economics.matching import match_straw_supply_and_demand
from residue_compass_economics.impact import compute_project_impact
from residue_compass_economics.validation import (
    validate_project_data as _validate_project_data,
    run_village_stress_tests,
)


def calculate_decision(
    forecast: VillageStrawForecast,
    economic_input: Optional[VillageEconomicInput] = None,
    assumptions: Optional[EconomicsConfig] = None,
) -> EconomicDecision:
    """Calculates deterministic comparative economics across KEEP, SELL, and FEED options."""
    return evaluate_village_economics(forecast, economic_input, assumptions)


def run_what_if(
    base_forecast: VillageStrawForecast,
    base_input: VillageEconomicInput,
    overrides: Dict[str, Any],
    assumptions: Optional[EconomicsConfig] = None,
) -> WhatIfResult:
    """Recalculates decisions under overridden agronomic, fuel, or market parameters."""
    return execute_what_if_analysis(base_forecast, base_input, overrides, assumptions)


def run_matching(
    forecasts: List[VillageStrawForecast],
    buyers: List[Buyer],
    balers: List[Baler],
    trucks: List[Truck],
    matching_config: Optional[MatchingConfig] = None,
    economics_config: Optional[EconomicsConfig] = None,
    distance_matrix: Optional[Dict[tuple, float]] = None,
) -> MatchingResult:
    """Executes deterministic supply-demand matching respecting all 12 operational constraints."""
    return match_straw_supply_and_demand(
        forecasts=forecasts,
        buyers=buyers,
        balers=balers,
        trucks=trucks,
        matching_config=matching_config,
        economics_config=economics_config,
        distance_matrix=distance_matrix,
    )


def calculate_impact(
    forecasts: List[VillageStrawForecast],
    bookings: List[MatchBooking],
    assumptions: Optional[EconomicsConfig] = None,
) -> ImpactSummary:
    """Computes transparent environmental, biomass diversion, and financial impact metrics."""
    return compute_project_impact(forecasts, bookings, assumptions)


def run_stress_tests(
    base_forecast: VillageStrawForecast,
    base_input: VillageEconomicInput,
    scenarios: Optional[List[StressScenario]] = None,
    assumptions: Optional[EconomicsConfig] = None,
) -> StressTestReport:
    """Runs a multi-scenario sensitivity and robustness test for a village."""
    return run_village_stress_tests(base_forecast, base_input, scenarios, assumptions)


def validate_project_data(
    forecasts: List[VillageStrawForecast],
    buyers: List[Buyer],
    balers: List[Baler],
    trucks: List[Truck],
) -> ValidationResult:
    """Validates structural integrity, capacity sanity, and calendar windows across entities."""
    return _validate_project_data(forecasts, buyers, balers, trucks)
