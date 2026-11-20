"""
Residue Compass - Part 4: Economics, Matching, and Validation.
"""

__version__ = "0.1.0"
__author__ = "Residue Compass Team"

from residue_compass_economics.config import EconomicsConfig, MatchingConfig
from residue_compass_economics.exceptions import (
    ResidueCompassError,
    ValidationError,
    InfeasibleMatchError,
    CalculationError,
)
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
from residue_compass_economics.service import (
    calculate_decision,
    run_what_if,
    run_matching,
    calculate_impact,
    run_stress_tests,
    validate_project_data,
)

__all__ = [
    "EconomicsConfig",
    "MatchingConfig",
    "ResidueCompassError",
    "ValidationError",
    "InfeasibleMatchError",
    "CalculationError",
    "VillageStrawForecast",
    "VillageEconomicInput",
    "EconomicDecision",
    "Buyer",
    "Baler",
    "Truck",
    "MatchBooking",
    "MatchingResult",
    "ImpactSummary",
    "StressScenario",
    "StressTestReport",
    "WhatIfResult",
    "ValidationResult",
    "calculate_decision",
    "run_what_if",
    "run_matching",
    "calculate_impact",
    "run_stress_tests",
    "validate_project_data",
]
