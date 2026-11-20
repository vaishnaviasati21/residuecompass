"""
Integration tests verifying the complete end-to-end pipeline:
Forecasts -> Data Validation -> Economics -> Matching -> Impact -> Stress Testing -> API Router.
"""

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from residue_compass_economics.sample_data import (
    get_sample_forecasts,
    get_sample_economic_inputs,
    get_sample_buyers,
    get_sample_balers,
    get_sample_trucks,
)
from residue_compass_economics.service import (
    calculate_decision,
    run_what_if,
    run_matching,
    calculate_impact,
    run_stress_tests,
    validate_project_data,
)
from residue_compass_economics.router import Part4APIRouter


class TestEndToEndIntegration(unittest.TestCase):
    def setUp(self):
        self.forecasts = get_sample_forecasts()
        self.econ_inputs = get_sample_economic_inputs()
        self.buyers = get_sample_buyers()
        self.balers = get_sample_balers()
        self.trucks = get_sample_trucks()

    def test_complete_service_pipeline(self):
        """Verifies that all core services work harmoniously with synthetic data."""
        # 1. Validation
        val_res = validate_project_data(self.forecasts, self.buyers, self.balers, self.trucks)
        self.assertTrue(val_res.is_valid, f"Validation failed with errors: {val_res.errors}")

        # 2. Economic Decisions across multiple villages
        # VIL-001 (Raikot) should recommend SELL
        d1 = calculate_decision(self.forecasts[0], self.econ_inputs["VIL-001"])
        self.assertEqual(d1.best_choice, "sell")

        # VIL-002 (Bhawanigarh) should recommend FEED
        d2 = calculate_decision(self.forecasts[1], self.econ_inputs["VIL-002"])
        self.assertEqual(d2.best_choice, "feed")

        # VIL-003 (Samana) should recommend KEEP
        d3 = calculate_decision(self.forecasts[2], self.econ_inputs["VIL-003"])
        self.assertEqual(d3.best_choice, "keep")

        # 3. Matching supply and demand
        match_res = run_matching(self.forecasts, self.buyers, self.balers, self.trucks)
        self.assertGreater(len(match_res.bookings), 0)
        self.assertGreater(match_res.total_matched_tonnes, 0.0)
        self.assertGreater(match_res.total_farmer_net_revenue_inr, 0.0)

        # 4. Impact calculation
        impact = calculate_impact(self.forecasts, match_res.bookings)
        self.assertEqual(impact.total_matched_tonnes, match_res.total_matched_tonnes)
        self.assertGreater(impact.estimated_tonnes_diverted, 0.0)

        # 5. Stress Testing on VIL-001
        stress_report = run_stress_tests(self.forecasts[0], self.econ_inputs["VIL-001"])
        self.assertEqual(stress_report.village_id, "VIL-001")
        self.assertEqual(len(stress_report.outcomes), 6)

    def test_api_router_serialization(self):
        """Verifies JSON round-trip compatibility for Part 1 API endpoints."""
        payload = {
            "forecast": self.forecasts[0].to_dict(),
            "economic_input": self.econ_inputs["VIL-001"].to_dict(),
        }
        res_dict = Part4APIRouter.handle_calculate_decision(payload)
        self.assertIn("best_choice", res_dict)
        self.assertEqual(res_dict["best_choice"], "sell")
        self.assertIn("break_even_price_inr_per_tonne", res_dict)

        # What-If route: drop offer to 1100 and fodder to 800 -> KEEP wins
        whatif_payload = {
            "forecast": self.forecasts[0].to_dict(),
            "economic_input": self.econ_inputs["VIL-001"].to_dict(),
            "overrides": {"offered_price": 1100.0, "fodder_value": 800.0},
        }
        whatif_res = Part4APIRouter.handle_what_if(whatif_payload)
        self.assertIn("updated_decision", whatif_res)
        self.assertEqual(whatif_res["updated_decision"]["best_choice"], "keep")


if __name__ == "__main__":
    unittest.main()
