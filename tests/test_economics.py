"""
Unit tests for the Economic Decision Engine.
Verifies keep/sell/feed comparison, hand-calculated break-even formulas, unit consistency,
cost-sharing overrides, and what-if sensitivity.
"""

import unittest
import sys
from pathlib import Path

# Ensure src is in python path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from residue_compass_economics.config import EconomicsConfig
from residue_compass_economics.schemas import VillageStrawForecast, VillageEconomicInput
from residue_compass_economics.economics import (
    calculate_keep_value,
    calculate_feed_value,
    calculate_seller_collection_costs,
    evaluate_village_economics,
    execute_what_if_analysis,
)
from residue_compass_economics.exceptions import ValidationError


class TestEconomicsEngine(unittest.TestCase):
    def setUp(self):
        self.config = EconomicsConfig()
        self.forecast = VillageStrawForecast(
            village_id="VIL-TEST-1",
            harvest_date="2026-10-20",
            collection_deadline="2026-11-05",
            straw_tonnes_low=80.0,
            straw_tonnes_expected=100.0,
            straw_tonnes_high=120.0,
            confidence="High",
            latitude=30.5,
            longitude=75.5,
            is_simulated=True,
        )

    def test_hand_verified_keep_value(self):
        """
        Verify hand arithmetic for KEEP:
        N: 6 kg * 6 INR = 36 INR
        P: 1.5 kg * 29.5 INR = 44.25 INR
        K: 15 kg * 34.0 INR = 510.0 INR
        S: 1.2 kg * 15.0 INR = 18.0 INR
        Total nutrient = 36 + 44.25 + 510 + 18 = 608.25 INR/t
        Soil organic benefit = 350 INR/t
        Gross Keep = 608.25 + 350 = 958.25 INR/t
        In-situ mulching cost = 520 INR/t
        Net Keep = 958.25 - 520 = 438.25 INR/t
        """
        net_keep, details = calculate_keep_value(self.config)
        self.assertAlmostEqual(net_keep, 438.25, places=2)
        self.assertAlmostEqual(details["gross_keep_benefit_inr_per_tonne"], 958.25, places=2)
        self.assertAlmostEqual(details["insitu_mulching_cost_inr_per_tonne"], 520.0, places=2)

    def test_hand_verified_feed_value(self):
        """
        Verify hand arithmetic for FEED:
        Default gross fodder value = 1800 INR/t
        Feed prep & urea treatment = 480 INR/t
        Local handling = 150 INR/t
        Total feed cost = 630 INR/t
        Net Feed = 1800 - 630 = 1170 INR/t
        """
        net_feed, details = calculate_feed_value(self.config)
        self.assertAlmostEqual(net_feed, 1170.0, places=2)
        self.assertAlmostEqual(details["total_feed_costs_inr_per_tonne"], 630.0, places=2)

    def test_hand_verified_break_even_price(self):
        """
        Verify break-even formula:
        break_even_price = max(net_keep, net_feed) + seller_costs
        Under custom input:
        local fodder value = 1000 INR/t -> net_feed = 1000 - 630 = 370 INR/t
        net_keep = 438.25 INR/t
        best_non_sell = 438.25 INR/t
        Distance = 10 km, transport rate = 5.50 INR/t-km -> transport = 55 INR/t
        Baling = 750 INR/t, loading = 180 INR/t
        Total seller costs = 750 + 180 + 55 = 985 INR/t
        Expected break-even price = 438.25 + 985 = 1423.25 INR/t
        """
        econ_input = VillageEconomicInput(
            village_id="VIL-TEST-1",
            offered_straw_price_inr_per_tonne=1423.25,
            buyer_distance_km=10.0,
            local_fodder_value_inr_per_tonne=1000.0,
        )
        decision = evaluate_village_economics(self.forecast, econ_input, self.config)
        self.assertAlmostEqual(decision.break_even_price_inr_per_tonne, 1423.25, places=2)
        self.assertAlmostEqual(decision.net_sell_value_inr_per_tonne, 438.25, places=2)
        self.assertAlmostEqual(decision.net_keep_value_inr_per_tonne, 438.25, places=2)

    def test_selling_clearly_beats_alternatives(self):
        """High offer (INR 2,400) and low distance (10 km) gives SELL as best choice."""
        econ_input = VillageEconomicInput(
            village_id="VIL-TEST-1",
            offered_straw_price_inr_per_tonne=2400.0,
            buyer_distance_km=10.0,
            local_fodder_value_inr_per_tonne=1200.0,  # net feed = 570
        )
        decision = evaluate_village_economics(self.forecast, econ_input, self.config)
        self.assertEqual(decision.best_choice, "sell")
        self.assertGreater(decision.net_sell_value_inr_per_tonne, decision.net_keep_value_inr_per_tonne)
        self.assertGreater(decision.net_sell_value_inr_per_tonne, decision.net_feed_value_inr_per_tonne)
        self.assertIn("SELL is recommended", decision.explanation)

    def test_keeping_beats_selling(self):
        """Low offer (INR 1,200) below break-even (INR 1,423.25) makes KEEP the winner."""
        econ_input = VillageEconomicInput(
            village_id="VIL-TEST-1",
            offered_straw_price_inr_per_tonne=1200.0,
            buyer_distance_km=10.0,
            local_fodder_value_inr_per_tonne=900.0,  # net feed = 270 < net keep = 438.25
        )
        decision = evaluate_village_economics(self.forecast, econ_input, self.config)
        self.assertEqual(decision.best_choice, "keep")
        self.assertIn("KEEP is recommended", decision.explanation)

    def test_feeding_beats_both_alternatives(self):
        """High dairy fodder value (INR 2,500/t) makes FEED the winner."""
        econ_input = VillageEconomicInput(
            village_id="VIL-TEST-1",
            offered_straw_price_inr_per_tonne=1800.0,
            buyer_distance_km=25.0,  # seller costs = 750 + 180 + 137.5 = 1067.5 -> net sell = 732.5
            local_fodder_value_inr_per_tonne=2500.0,  # net feed = 2500 - 630 = 1870
        )
        decision = evaluate_village_economics(self.forecast, econ_input, self.config)
        self.assertEqual(decision.best_choice, "feed")
        self.assertIn("FEED is recommended", decision.explanation)

    def test_high_transport_distance_reverses_sell_recommendation(self):
        """Increasing transport distance from 15km to 90km turns SELL into KEEP."""
        base_input = VillageEconomicInput(
            village_id="VIL-TEST-1",
            offered_straw_price_inr_per_tonne=1700.0,
            buyer_distance_km=15.0,
            local_fodder_value_inr_per_tonne=800.0,
        )
        near_decision = evaluate_village_economics(self.forecast, base_input, self.config)
        self.assertEqual(near_decision.best_choice, "sell")

        what_if_res = execute_what_if_analysis(
            self.forecast, base_input, {"distance_km": 90.0}, self.config
        )
        self.assertEqual(what_if_res.updated_decision.best_choice, "keep")
        self.assertIn("best_choice", what_if_res.changed_fields)

    def test_buyer_covers_logistics_boosts_seller_revenue(self):
        """When buyer absorbs transport and baling, farmer costs drop to loading only."""
        econ_input = VillageEconomicInput(
            village_id="VIL-TEST-1",
            offered_straw_price_inr_per_tonne=1600.0,
            buyer_distance_km=50.0,
            buyer_covers_transport=True,
            buyer_covers_baling=True,
        )
        decision = evaluate_village_economics(self.forecast, econ_input, self.config)
        # Incurred cost = loading only (180 INR/t)
        # Net sell = 1600 - 180 = 1420 INR/t
        self.assertEqual(decision.best_choice, "sell")
        self.assertAlmostEqual(decision.net_sell_value_inr_per_tonne, 1420.0, places=2)

    def test_zero_distance_and_extreme_prices(self):
        """Validates edge conditions: 0km distance and extreme prices."""
        # 0km distance (on-site co-located plant)
        costs, breakdown = calculate_seller_collection_costs(0.0, self.config)
        self.assertAlmostEqual(breakdown["transport_cost_inr_per_tonne"], 0.0)

        # Negative costs or distance must raise ValidationError
        with self.assertRaises(ValidationError):
            calculate_seller_collection_costs(-5.0, self.config)

    def test_price_range_recommendations(self):
        """Verifies recommended price low and high bands are strictly greater than break-even."""
        decision = evaluate_village_economics(self.forecast, None, self.config)
        self.assertGreater(decision.recommended_price_low_inr_per_tonne, decision.break_even_price_inr_per_tonne)
        self.assertGreater(decision.recommended_price_high_inr_per_tonne, decision.recommended_price_low_inr_per_tonne)


if __name__ == "__main__":
    unittest.main()
