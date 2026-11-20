"""
Unit tests for the Spatio-Temporal Supply-Demand Matching Engine.
Verifies all 12 operational hard constraints:
1. Village supply limits
2. Buyer demand limits
3. Baler capacity limits
4. Truck capacity limits
5. Resource availability windows
6. Straw ready dates
7. Collection sowing deadlines
8. Resource double-booking prevention
9. Expired buyer offers
10. ID integrity
11. Partial allocation tracking
12. Deterministic execution
"""

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from residue_compass_economics.schemas import (
    VillageStrawForecast,
    Buyer,
    Baler,
    Truck,
)
from residue_compass_economics.config import MatchingConfig, EconomicsConfig
from residue_compass_economics.matching import (
    match_straw_supply_and_demand,
    haversine_distance_km,
)
from residue_compass_economics.exceptions import ValidationError


class TestMatchingEngine(unittest.TestCase):
    def setUp(self):
        self.m_cfg = MatchingConfig(max_search_radius_km=100.0, min_dispatch_tonnes=5.0)
        self.e_cfg = EconomicsConfig()

        self.village = VillageStrawForecast(
            village_id="VIL-101",
            harvest_date="2026-10-20",
            collection_deadline="2026-11-04",
            straw_tonnes_low=80.0,
            straw_tonnes_expected=100.0,
            straw_tonnes_high=120.0,
            confidence="High",
            latitude=30.50,
            longitude=75.50,
            is_simulated=True,
        )

        self.buyer = Buyer(
            buyer_id="BUY-101",
            name="Alpha Biomass Power",
            latitude=30.60,
            longitude=75.55,
            max_demand_tonnes=150.0,
            remaining_demand_tonnes=150.0,
            offered_price_inr_per_tonne=2100.0,
            valid_from="2026-10-15",
            valid_until="2026-11-15",
            is_simulated=True,
        )

        self.baler = Baler(
            baler_id="BAL-101",
            owner_name="Aggarwal CHC Baler",
            latitude=30.52,
            longitude=75.51,
            daily_capacity_tonnes=60.0,
            cost_per_tonne_inr=700.0,
            available_from="2026-10-18",
            available_until="2026-11-10",
            is_operational=True,
            is_simulated=True,
        )

        self.truck = Truck(
            truck_id="TRK-101",
            transporter_name="Kisan Flatbed 50T",
            latitude=30.51,
            longitude=75.52,
            daily_capacity_tonnes=50.0,
            cost_per_tonne_km_inr=5.0,
            fixed_base_cost_inr=1000.0,
            available_from="2026-10-18",
            available_until="2026-11-10",
            is_operational=True,
            is_simulated=True,
        )

    def test_haversine_proxy_distance_accuracy(self):
        """Verifies straight-line haversine computation with winding factor."""
        dist = haversine_distance_km(30.0, 75.0, 30.0, 75.0)
        self.assertEqual(dist, 0.0)

        # ~11 km straight line between (30.5, 75.5) and (30.6, 75.55)
        # Scaled by 1.28 proxy factor = ~18.5 km
        dist2 = haversine_distance_km(30.50, 75.50, 30.60, 75.55, road_winding_factor=1.28)
        self.assertGreater(dist2, 12.0)
        self.assertLess(dist2, 25.0)

        # Coordinate limits check
        with self.assertRaises(ValidationError):
            haversine_distance_km(95.0, 75.0, 30.0, 75.0)

    def test_single_feasible_match_respects_capacities(self):
        """
        Village has 100t, Buyer wants 150t, Baler capacity = 60t, Truck capacity = 50t.
        In a single booking on the pickup date, truck is bottleneck (50t).
        Matched tonnes must equal 50t. Remaining village = 50t.
        """
        res = match_straw_supply_and_demand(
            forecasts=[self.village],
            buyers=[self.buyer],
            balers=[self.baler],
            trucks=[self.truck],
            matching_config=self.m_cfg,
            economics_config=self.e_cfg,
        )
        self.assertEqual(len(res.bookings), 1)
        booking = res.bookings[0]
        self.assertEqual(booking.matched_tonnes, 50.0)
        self.assertEqual(booking.village_id, "VIL-101")
        self.assertEqual(booking.buyer_id, "BUY-101")
        self.assertGreaterEqual(booking.pickup_date, self.village.harvest_date)
        self.assertLessEqual(booking.pickup_date, self.village.collection_deadline)

        # Partial remaining supply
        self.assertEqual(res.total_matched_tonnes, 50.0)
        self.assertEqual(res.total_unmatched_tonnes, 50.0)
        self.assertEqual(len(res.unmatched_villages), 1)
        self.assertEqual(res.unmatched_villages[0].remaining_unmatched_tonnes, 50.0)

    def test_harvest_window_violation_prevention(self):
        """If buyer expires before village harvest starts, no match can be booked."""
        self.buyer.valid_until = "2026-10-19"  # Village harvests 2026-10-20
        res = match_straw_supply_and_demand(
            forecasts=[self.village],
            buyers=[self.buyer],
            balers=[self.baler],
            trucks=[self.truck],
            matching_config=self.m_cfg,
            economics_config=self.e_cfg,
        )
        self.assertEqual(len(res.bookings), 0)
        self.assertEqual(res.total_matched_tonnes, 0.0)
        self.assertEqual(res.total_unmatched_tonnes, 100.0)

    def test_deadline_sowing_window_enforced(self):
        """If machinery is only available after collection deadline, no match can be booked."""
        # Village deadline is 2026-11-04. Baler available only starting 2026-11-06.
        self.baler.available_from = "2026-11-06"
        res = match_straw_supply_and_demand(
            forecasts=[self.village],
            buyers=[self.buyer],
            balers=[self.baler],
            trucks=[self.truck],
            matching_config=self.m_cfg,
            economics_config=self.e_cfg,
        )
        self.assertEqual(len(res.bookings), 0)

    def test_no_silent_double_booking_same_resource(self):
        """
        Two villages harvest on same day and require same baler and truck.
        Both villages want 40 tonnes.
        Baler has 60 tonnes daily capacity. Truck has 50 tonnes daily capacity.
        Truck can haul 50 tonnes total on that day.
        First village gets 40 tonnes.
        Second village can get at most 10 tonnes on that same day.
        Total hauled on that day must NOT exceed 50 tonnes!
        """
        v1 = VillageStrawForecast(
            village_id="VIL-A",
            harvest_date="2026-10-20",
            collection_deadline="2026-10-21",  # Tight 2-day window
            straw_tonnes_low=35.0,
            straw_tonnes_expected=40.0,
            straw_tonnes_high=45.0,
            confidence="High",
            latitude=30.50,
            longitude=75.50,
        )
        v2 = VillageStrawForecast(
            village_id="VIL-B",
            harvest_date="2026-10-20",
            collection_deadline="2026-10-21",  # Same tight 2-day window
            straw_tonnes_low=35.0,
            straw_tonnes_expected=40.0,
            straw_tonnes_high=45.0,
            confidence="High",
            latitude=30.51,
            longitude=75.51,
        )
        res = match_straw_supply_and_demand(
            forecasts=[v1, v2],
            buyers=[self.buyer],
            balers=[self.baler],
            trucks=[self.truck],
            matching_config=self.m_cfg,
            economics_config=self.e_cfg,
        )
        # Check sum of bookings on 2026-10-20
        oct20_tonnes = sum(b.matched_tonnes for b in res.bookings if b.pickup_date == "2026-10-20")
        self.assertLessEqual(oct20_tonnes, self.truck.daily_capacity_tonnes)
        self.assertLessEqual(oct20_tonnes, self.baler.daily_capacity_tonnes)

    def test_deterministic_repeat_runs(self):
        """Executing matching multiple times with identical inputs produces identical results."""
        res1 = match_straw_supply_and_demand(
            forecasts=[self.village],
            buyers=[self.buyer],
            balers=[self.baler],
            trucks=[self.truck],
            matching_config=self.m_cfg,
            economics_config=self.e_cfg,
        )
        res2 = match_straw_supply_and_demand(
            forecasts=[self.village],
            buyers=[self.buyer],
            balers=[self.baler],
            trucks=[self.truck],
            matching_config=self.m_cfg,
            economics_config=self.e_cfg,
        )
        self.assertEqual(len(res1.bookings), len(res2.bookings))
        self.assertEqual(res1.total_matched_tonnes, res2.total_matched_tonnes)
        self.assertEqual(res1.bookings[0].match_id, res2.bookings[0].match_id)
        self.assertEqual(res1.bookings[0].matched_tonnes, res2.bookings[0].matched_tonnes)


if __name__ == "__main__":
    unittest.main()
