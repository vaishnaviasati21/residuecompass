"""
Unit tests for Validation and Multi-Scenario Stress Testing.
"""

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from residue_compass_economics.schemas import (
    VillageStrawForecast,
    VillageEconomicInput,
    Buyer,
    Baler,
    Truck,
)
from residue_compass_economics.config import EconomicsConfig
from residue_compass_economics.validation import (
    validate_project_data,
    run_village_stress_tests,
    generate_standard_stress_scenarios,
)
from residue_compass_economics.exceptions import ValidationError


class TestValidationAndStress(unittest.TestCase):
    def setUp(self):
        self.config = EconomicsConfig()
        self.forecast = VillageStrawForecast(
            village_id="VIL-VAL-1",
            harvest_date="2026-10-20",
            collection_deadline="2026-11-05",
            straw_tonnes_low=80.0,
            straw_tonnes_expected=100.0,
            straw_tonnes_high=120.0,
            confidence="High",
            latitude=30.2,
            longitude=75.8,
        )
        self.buyer = Buyer(
            buyer_id="BUY-VAL-1",
            name="Val Buyer",
            latitude=30.3,
            longitude=75.9,
            max_demand_tonnes=100.0,
            remaining_demand_tonnes=100.0,
            offered_price_inr_per_tonne=2000.0,
            valid_from="2026-10-18",
            valid_until="2026-11-15",
        )
        self.baler = Baler(
            baler_id="BAL-VAL-1",
            owner_name="Val Baler",
            latitude=30.25,
            longitude=75.85,
            daily_capacity_tonnes=50.0,
            cost_per_tonne_inr=700.0,
            available_from="2026-10-18",
            available_until="2026-11-15",
        )
        self.truck = Truck(
            truck_id="TRK-VAL-1",
            transporter_name="Val Truck",
            latitude=30.25,
            longitude=75.85,
            daily_capacity_tonnes=40.0,
            cost_per_tonne_km_inr=5.0,
            fixed_base_cost_inr=1000.0,
            available_from="2026-10-18",
            available_until="2026-11-15",
        )

    def test_schema_validations_and_boundary_checks(self):
        """Verifies duplicate ID detection and capacity checks."""
        # Duplicate village ID check
        dup_forecast = VillageStrawForecast(
            village_id="VIL-VAL-1",  # duplicate!
            harvest_date="2026-10-21",
            straw_tonnes_low=50.0,
            straw_tonnes_expected=60.0,
            straw_tonnes_high=70.0,
            confidence="Low",
        )
        val_res = validate_project_data([self.forecast, dup_forecast], [self.buyer], [self.baler], [self.truck])
        self.assertFalse(val_res.is_valid)
        self.assertTrue(any("Duplicate village_id" in err for err in val_res.errors))

    def test_invalid_forecast_ordering_raises(self):
        """low > expected or expected > high raises ValidationError."""
        with self.assertRaises(ValidationError):
            VillageStrawForecast(
                village_id="VIL-ERR",
                harvest_date="2026-10-20",
                straw_tonnes_low=120.0,  # low > expected!
                straw_tonnes_expected=100.0,
                straw_tonnes_high=150.0,
                confidence="High",
            )

    def test_stress_testing_detects_recommendation_flips(self):
        """
        Runs the 6 standard stress scenarios.
        Shows that under high transport distance or biomass price drop, SELL flips to KEEP or FEED.
        """
        econ_input = VillageEconomicInput(
            village_id="VIL-VAL-1",
            offered_straw_price_inr_per_tonne=1700.0,
            buyer_distance_km=15.0,
            local_fodder_value_inr_per_tonne=1200.0,
        )
        report = run_village_stress_tests(self.forecast, econ_input, config=self.config)

        self.assertEqual(len(report.outcomes), 6)
        # Check specific scenario outcomes
        diesel_sc = next(o for o in report.outcomes if o.scenario_id == "STRESS-DIESEL-SPIKE")
        self.assertGreater(diesel_sc.scenario_break_even_price, diesel_sc.baseline_break_even_price)

        drop_sc = next(o for o in report.outcomes if o.scenario_id == "STRESS-BUYER-PRICE-DROP")
        self.assertTrue(drop_sc.choice_changed)
        self.assertNotEqual(drop_sc.scenario_choice, "sell")


if __name__ == "__main__":
    unittest.main()
