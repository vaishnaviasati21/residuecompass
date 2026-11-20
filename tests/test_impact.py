"""
Unit tests for Transparent Impact Estimation.
Verifies biomass diversion, revenue aggregation, division-by-zero protection,
and handling of unconfirmed or cancelled bookings.
"""

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from residue_compass_economics.schemas import VillageStrawForecast, MatchBooking
from residue_compass_economics.config import EconomicsConfig
from residue_compass_economics.impact import compute_project_impact


class TestImpactEngine(unittest.TestCase):
    def setUp(self):
        self.config = EconomicsConfig()
        self.forecasts = [
            VillageStrawForecast(
                village_id="VIL-01",
                harvest_date="2026-10-20",
                straw_tonnes_low=90.0,
                straw_tonnes_expected=100.0,
                straw_tonnes_high=110.0,
                confidence="High",
            ),
            VillageStrawForecast(
                village_id="VIL-02",
                harvest_date="2026-10-22",
                straw_tonnes_low=140.0,
                straw_tonnes_expected=150.0,
                straw_tonnes_high=160.0,
                confidence="Medium",
            ),
        ]

    def test_impact_calculation_accuracy(self):
        """Verifies calculation of tonnes diverted and farmer revenue."""
        bookings = [
            MatchBooking(
                match_id="MB-001",
                village_id="VIL-01",
                buyer_id="BUY-01",
                baler_id="BAL-01",
                truck_id="TRK-01",
                pickup_date="2026-10-21",
                matched_tonnes=80.0,
                price_inr_per_tonne=2000.0,
                transport_distance_km=15.0,
                transport_cost_inr=6000.0,
                baling_cost_inr=56000.0,
                loading_cost_inr=14400.0,
                total_cost_inr=76400.0,
                estimated_farmer_net_revenue_inr=83600.0,
                estimated_saving_vs_burning_inr=103600.0,
                estimated_tonnes_diverted=80.0,
                status="CONFIRMED",
            )
        ]
        impact = compute_project_impact(self.forecasts, bookings, self.config)

        self.assertEqual(impact.total_forecast_straw_tonnes, 250.0)
        self.assertEqual(impact.total_matched_tonnes, 80.0)
        self.assertEqual(impact.total_unmatched_tonnes, 170.0)
        self.assertAlmostEqual(impact.matched_fraction, 0.32, places=2)
        self.assertEqual(impact.estimated_tonnes_diverted, 80.0)
        self.assertEqual(impact.estimated_farmer_net_revenue_inr, 83600.0)
        self.assertIn("Transparency & Verification Notice", impact.confidence_and_limitations)

    def test_zero_forecast_division_guard(self):
        """Guards against ZeroDivisionError when total forecast straw is 0."""
        impact = compute_project_impact([], [], self.config)
        self.assertEqual(impact.total_forecast_straw_tonnes, 0.0)
        self.assertEqual(impact.matched_fraction, 0.0)

    def test_cancelled_bookings_excluded(self):
        """Cancelled bookings must not count towards tonnes diverted or farmer revenue."""
        cancelled_booking = MatchBooking(
            match_id="MB-CANCELLED",
            village_id="VIL-01",
            buyer_id="BUY-01",
            baler_id="BAL-01",
            truck_id="TRK-01",
            pickup_date="2026-10-21",
            matched_tonnes=50.0,
            price_inr_per_tonne=2000.0,
            transport_distance_km=15.0,
            transport_cost_inr=3000.0,
            baling_cost_inr=35000.0,
            loading_cost_inr=9000.0,
            total_cost_inr=47000.0,
            estimated_farmer_net_revenue_inr=53000.0,
            estimated_saving_vs_burning_inr=65500.0,
            estimated_tonnes_diverted=50.0,
            status="CANCELLED",
        )
        impact = compute_project_impact(self.forecasts, [cancelled_booking], self.config)
        self.assertEqual(impact.total_matched_tonnes, 0.0)
        self.assertEqual(impact.estimated_tonnes_diverted, 0.0)
        self.assertEqual(impact.estimated_farmer_net_revenue_inr, 0.0)
        self.assertEqual(impact.assumptions_summary["cancelled_bookings_count"], 1)


if __name__ == "__main__":
    unittest.main()
