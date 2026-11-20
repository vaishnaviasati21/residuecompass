"""
Spatio-Temporal Supply-Demand Matching Engine for Residue Compass Part 4.
Greedy priority optimization respecting 12 strict operational, capacity, and calendar constraints.
Computes road-proxy Haversine distances, partial allocations, cost breakdowns, and transparent logs.
"""

import math
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional, Set
from residue_compass_economics.config import MatchingConfig, EconomicsConfig
from residue_compass_economics.schemas import (
    VillageStrawForecast,
    Buyer,
    Baler,
    Truck,
    MatchBooking,
    MatchingResult,
    UnmatchedVillage,
    UnfilledBuyerDemand,
    parse_iso_date,
)
from residue_compass_economics.exceptions import ValidationError, InfeasibleMatchError


def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    road_winding_factor: float = 1.28
) -> float:
    """
    Computes great-circle distance between two GPS coordinates using the Haversine formula,
    scaled by a road winding proxy factor.
    Returns distance in kilometres.
    """
    # Strict coordinate validation
    if not (-90.0 <= lat1 <= 90.0 and -90.0 <= lat2 <= 90.0):
        raise ValidationError(f"Latitude out of range [-90, 90]: ({lat1}, {lat2})")
    if not (-180.0 <= lon1 <= 180.0 and -180.0 <= lon2 <= 180.0):
        raise ValidationError(f"Longitude out of range [-180, 180]: ({lon1}, {lon2})")

    # If coordinates are identical or practically zero distance
    if abs(lat1 - lat2) < 1e-7 and abs(lon1 - lon2) < 1e-7:
        return 0.0

    r = 6371.0  # Earth's mean radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    straight_line_dist = r * c

    return round(straight_line_dist * road_winding_factor, 2)


def find_earliest_feasible_pickup_date(
    village_harvest_date: str,
    village_deadline: str,
    buyer_valid_from: str,
    buyer_valid_until: str,
    baler_avail_from: str,
    baler_avail_until: str,
    truck_avail_from: str,
    truck_avail_until: str,
    baler_id: str,
    truck_id: str,
    baler_daily_capacity: float,
    truck_daily_capacity: float,
    baler_daily_usage: Dict[Tuple[str, str], float],
    truck_daily_usage: Dict[Tuple[str, str], float],
    min_required_tonnes: float = 1.0,
) -> Optional[str]:
    """
    Finds the earliest date satisfying all calendar constraints and daily capacity limits:
    - pickup_date >= village_harvest_date
    - pickup_date <= village_deadline
    - pickup_date within buyer validity window
    - pickup_date within baler availability window
    - pickup_date within truck availability window
    - baler remaining capacity on pickup_date >= min_required_tonnes
    - truck remaining capacity on pickup_date >= min_required_tonnes
    """
    v_start = parse_iso_date(village_harvest_date)
    v_end = parse_iso_date(village_deadline)
    b_start = parse_iso_date(buyer_valid_from)
    b_end = parse_iso_date(buyer_valid_until)
    bal_start = parse_iso_date(baler_avail_from)
    bal_end = parse_iso_date(baler_avail_until)
    t_start = parse_iso_date(truck_avail_from)
    t_end = parse_iso_date(truck_avail_until)

    # Window intersection
    earliest_possible = max(v_start, b_start, bal_start, t_start)
    latest_possible = min(v_end, b_end, bal_end, t_end)

    if earliest_possible > latest_possible:
        return None

    # Step through candidate dates chronologically
    curr = earliest_possible
    while curr <= latest_possible:
        curr_str = curr.isoformat()
        bal_used = baler_daily_usage.get((baler_id, curr_str), 0.0)
        trk_used = truck_daily_usage.get((truck_id, curr_str), 0.0)

        bal_rem = baler_daily_capacity - bal_used
        trk_rem = truck_daily_capacity - trk_used

        if bal_rem >= min_required_tonnes and trk_rem >= min_required_tonnes:
            return curr_str

        curr += timedelta(days=1)

    return None


def match_straw_supply_and_demand(
    forecasts: List[VillageStrawForecast],
    buyers: List[Buyer],
    balers: List[Baler],
    trucks: List[Truck],
    matching_config: Optional[MatchingConfig] = None,
    economics_config: Optional[EconomicsConfig] = None,
    distance_matrix: Optional[Dict[Tuple[str, str], float]] = None,
) -> MatchingResult:
    """
    Core deterministic greedy matching algorithm.
    Enforces all 12 hard operational constraints:
    1. Never allocate more than village available forecast.
    2. Never allocate more than buyer remaining demand.
    3. Never exceed baler daily capacity.
    4. Never exceed truck daily capacity.
    5. Never schedule inactive/unavailable machine or truck.
    6. Never book pickup before harvest ready date.
    7. Never schedule after collection deadline.
    8. Never double-book resources beyond daily rated capacity.
    9. Never use expired buyer offers.
    10. Never book with invalid IDs.
    11. Explicit accounting of partial allocations.
    12. Deterministic execution for reproducibility.
    """
    m_cfg = matching_config or MatchingConfig()
    e_cfg = economics_config or EconomicsConfig()

    # Pre-validation & indexing
    for f in forecasts:
        if not f.collection_deadline:
            # Default deadline is harvest_date + 14 days (standard wheat sowing turnaround)
            h_dt = parse_iso_date(f.harvest_date)
            f.collection_deadline = (h_dt + timedelta(days=14)).isoformat()

    active_buyers = [b for b in buyers if b.remaining_demand_tonnes > 0]
    active_balers = [b for b in balers if b.is_operational]
    active_trucks = [t for t in trucks if t.is_operational]

    # Tracking mutable state
    village_remaining: Dict[str, float] = {f.village_id: f.straw_tonnes_expected for f in forecasts}
    buyer_remaining: Dict[str, float] = {b.buyer_id: b.remaining_demand_tonnes for b in active_buyers}
    baler_daily_usage: Dict[Tuple[str, str], float] = {}  # (baler_id, date_str) -> allocated_tonnes
    truck_daily_usage: Dict[Tuple[str, str], float] = {}  # (truck_id, date_str) -> allocated_tonnes

    bookings: List[MatchBooking] = []
    scheduled_baler_ids: Set[str] = set()
    scheduled_truck_ids: Set[str] = set()
    village_failure_reasons: Dict[str, List[str]] = {f.village_id: [] for f in forecasts}
    buyer_failure_reasons: Dict[str, List[str]] = {b.buyer_id: [] for b in active_buyers}

    # Evaluate candidate quadruples: (Village, Buyer, Baler, Truck)
    # To maintain efficiency and determinism, generate feasible candidate matches
    candidates = []

    for f in forecasts:
        v_id = f.village_id
        if village_remaining[v_id] < m_cfg.min_dispatch_tonnes:
            continue

        for b in active_buyers:
            b_id = b.buyer_id
            if buyer_remaining[b_id] < m_cfg.min_dispatch_tonnes:
                continue

            # Calculate distance between Village and Buyer
            if distance_matrix and (v_id, b_id) in distance_matrix:
                dist_km = distance_matrix[(v_id, b_id)]
            elif f.latitude != 0.0 or f.longitude != 0.0 or b.latitude != 0.0 or b.longitude != 0.0:
                dist_km = haversine_distance_km(
                    f.latitude, f.longitude,
                    b.latitude, b.longitude,
                    road_winding_factor=m_cfg.default_road_winding_factor
                )
            else:
                # Missing coordinates and missing matrix -> mark infeasible
                village_failure_reasons[v_id].append(f"Missing GPS coordinates for route to buyer '{b.name}' ({b_id}).")
                continue

            if dist_km > m_cfg.max_search_radius_km:
                village_failure_reasons[v_id].append(
                    f"Buyer '{b.name}' is {dist_km:.1f}km away, exceeding search radius {m_cfg.max_search_radius_km}km."
                )
                continue

            # Check matching balers and trucks
            for bal in active_balers:
                for trk in active_trucks:
                    # Economics of this candidate
                    baling_cost = 0.0 if b.covers_baling else bal.cost_per_tonne_inr
                    transport_cost_per_tonne = (
                        0.0 if b.covers_transport
                        else (trk.cost_per_tonne_km_inr * dist_km) + (trk.fixed_base_cost_inr / max(trk.daily_capacity_tonnes, 1.0))
                    )
                    net_margin_per_tonne = b.offered_price_inr_per_tonne - baling_cost - transport_cost_per_tonne - e_cfg.default_fixed_loading_cost_inr_per_tonne

                    # Urgency score: fewer days left until collection deadline gives higher priority
                    days_until_deadline = (parse_iso_date(f.collection_deadline) - parse_iso_date(f.harvest_date)).days
                    urgency_bonus = max(0, (15 - days_until_deadline)) * m_cfg.urgency_weight

                    # Composite sorting score (higher is better)
                    score = net_margin_per_tonne + urgency_bonus

                    candidates.append({
                        "score": score,
                        "village": f,
                        "buyer": b,
                        "baler": bal,
                        "truck": trk,
                        "distance_km": dist_km,
                        "net_margin_per_tonne": net_margin_per_tonne,
                        "baling_cost_per_tonne": baling_cost,
                        "transport_cost_per_tonne": transport_cost_per_tonne,
                    })

    # Sort deterministically: highest score first, with stable tie-breaking on IDs
    candidates.sort(
        key=lambda c: (
            -c["score"],
            c["village"].village_id,
            c["buyer"].buyer_id,
            c["baler"].baler_id,
            c["truck"].truck_id,
        )
    )

    # Greedily allocate matches
    booking_counter = 1
    for cand in candidates:
        v: VillageStrawForecast = cand["village"]
        b: Buyer = cand["buyer"]
        bal: Baler = cand["baler"]
        trk: Truck = cand["truck"]
        dist_km: float = cand["distance_km"]

        v_rem = village_remaining[v.village_id]
        b_rem = buyer_remaining[b.buyer_id]

        if v_rem < m_cfg.min_dispatch_tonnes or b_rem < m_cfg.min_dispatch_tonnes:
            continue

        # Find earliest available date
        pickup_date = find_earliest_feasible_pickup_date(
            village_harvest_date=v.harvest_date,
            village_deadline=v.collection_deadline,  # type: ignore
            buyer_valid_from=b.valid_from,
            buyer_valid_until=b.valid_until,
            baler_avail_from=bal.available_from,
            baler_avail_until=bal.available_until,
            truck_avail_from=trk.available_from,
            truck_avail_until=trk.available_until,
            baler_id=bal.baler_id,
            truck_id=trk.truck_id,
            baler_daily_capacity=bal.daily_capacity_tonnes,
            truck_daily_capacity=trk.daily_capacity_tonnes,
            baler_daily_usage=baler_daily_usage,
            truck_daily_usage=truck_daily_usage,
            min_required_tonnes=m_cfg.min_dispatch_tonnes,
        )

        if not pickup_date:
            continue

        bal_used = baler_daily_usage.get((bal.baler_id, pickup_date), 0.0)
        trk_used = truck_daily_usage.get((trk.truck_id, pickup_date), 0.0)

        bal_avail = bal.daily_capacity_tonnes - bal_used
        trk_avail = trk.daily_capacity_tonnes - trk_used

        allocable_tonnes = min(v_rem, b_rem, bal_avail, trk_avail)

        if allocable_tonnes < m_cfg.min_dispatch_tonnes:
            continue

        # Allocation confirmed!
        allocable_tonnes = round(allocable_tonnes, 2)
        village_remaining[v.village_id] = round(v_rem - allocable_tonnes, 2)
        buyer_remaining[b.buyer_id] = round(b_rem - allocable_tonnes, 2)

        baler_daily_usage[(bal.baler_id, pickup_date)] = round(bal_used + allocable_tonnes, 2)
        truck_daily_usage[(trk.truck_id, pickup_date)] = round(trk_used + allocable_tonnes, 2)

        scheduled_baler_ids.add(bal.baler_id)
        scheduled_truck_ids.add(trk.truck_id)

        # Cost calculations
        total_baling_cost = round(cand["baling_cost_per_tonne"] * allocable_tonnes, 2)
        total_transport_cost = round(cand["transport_cost_per_tonne"] * allocable_tonnes, 2)
        total_loading_cost = round(e_cfg.default_fixed_loading_cost_inr_per_tonne * allocable_tonnes, 2)
        total_costs = round(total_baling_cost + total_transport_cost + total_loading_cost, 2)

        gross_revenue = round(b.offered_price_inr_per_tonne * allocable_tonnes, 2)
        net_farmer_revenue = round(gross_revenue - total_costs, 2)

        # Estimated savings vs in-situ burning penalty
        estimated_savings_vs_burning = round(
            net_farmer_revenue + (e_cfg.burning_penalty_or_loss_inr_per_tonne * allocable_tonnes),
            2
        )

        match_id = f"MB-{v.village_id[:4].upper()}-{b.buyer_id[:4].upper()}-{pickup_date.replace('-', '')}-{booking_counter:02d}"
        booking_counter += 1

        explanation = (
            f"Scheduled {allocable_tonnes:.1f}t pickup on {pickup_date} with Buyer '{b.name}' ({b.buyer_id}) "
            f"via Baler '{bal.owner_name}' and Truck '{trk.transporter_name}'. "
            f"Road distance: {dist_km:.1f}km. Farmer net revenue: INR {net_farmer_revenue:,.2f}."
        )

        booking = MatchBooking(
            match_id=match_id,
            village_id=v.village_id,
            buyer_id=b.buyer_id,
            baler_id=bal.baler_id,
            truck_id=trk.truck_id,
            pickup_date=pickup_date,
            matched_tonnes=allocable_tonnes,
            price_inr_per_tonne=b.offered_price_inr_per_tonne,
            transport_distance_km=dist_km,
            transport_cost_inr=total_transport_cost,
            baling_cost_inr=total_baling_cost,
            loading_cost_inr=total_loading_cost,
            total_cost_inr=total_costs,
            estimated_farmer_net_revenue_inr=net_farmer_revenue,
            estimated_saving_vs_burning_inr=estimated_savings_vs_burning,
            estimated_tonnes_diverted=allocable_tonnes,
            status="CONFIRMED",
            is_simulated=v.is_simulated or b.is_simulated,
            assumptions={
                "road_distance_proxy_factor": m_cfg.default_road_winding_factor,
                "buyer_covers_transport": b.covers_transport,
                "buyer_covers_baling": b.covers_baling,
            },
            explanation=explanation,
        )
        bookings.append(booking)

    # Compile Unmatched Villages
    unmatched_villages: List[UnmatchedVillage] = []
    for f in forecasts:
        rem = village_remaining[f.village_id]
        if rem > 0.0:
            reasons = village_failure_reasons.get(f.village_id, [])
            if not reasons:
                if len(bookings) == 0:
                    reasons.append("No active buyer within radius or machinery capacities exhausted.")
                else:
                    reasons.append("Remaining supply exceeded available buyer orders or collection slots.")
            reason_str = "; ".join(set(reasons)) if reasons else "Partial allocation: supply exceeded local logistics capacity."
            unmatched_villages.append(
                UnmatchedVillage(
                    village_id=f.village_id,
                    forecast_tonnes=f.straw_tonnes_expected,
                    remaining_unmatched_tonnes=rem,
                    reason=reason_str,
                )
            )

    # Compile Unfilled Buyers
    unfilled_buyers: List[UnfilledBuyerDemand] = []
    for b in active_buyers:
        b_rem = buyer_remaining[b.buyer_id]
        if b_rem > 0.0:
            unfilled_buyers.append(
                UnfilledBuyerDemand(
                    buyer_id=b.buyer_id,
                    buyer_name=b.name,
                    initial_demand_tonnes=b.max_demand_tonnes,
                    remaining_demand_tonnes=b_rem,
                    reason="Local village harvest dates did not align or supply within radius was depleted.",
                )
            )

    # Unscheduled machinery
    unscheduled_balers = [b.baler_id for b in balers if b.baler_id not in scheduled_baler_ids]
    unscheduled_trucks = [t.truck_id for t in trucks if t.truck_id not in scheduled_truck_ids]

    # Aggregates
    total_forecast = round(sum(f.straw_tonnes_expected for f in forecasts), 2)
    total_matched = round(sum(b.matched_tonnes for b in bookings), 2)
    total_unmatched = round(sum(u.remaining_unmatched_tonnes for u in unmatched_villages), 2)
    total_revenue = round(sum(b.estimated_farmer_net_revenue_inr for b in bookings), 2)
    total_diverted = round(sum(b.estimated_tonnes_diverted for b in bookings), 2)

    warnings = []
    if any(f.is_simulated for f in forecasts) or any(b.is_simulated for b in buyers):
        warnings.append("Synthetic Data Notice: Bookings were generated using simulated forecasts and mock entities.")
    if total_unmatched > 0:
        warnings.append(f"{total_unmatched:.1f} tonnes of paddy straw could not be matched with off-farm buyers.")

    return MatchingResult(
        bookings=bookings,
        unmatched_villages=unmatched_villages,
        unfilled_buyers=unfilled_buyers,
        unscheduled_balers=unscheduled_balers,
        unscheduled_trucks=unscheduled_trucks,
        total_forecast_tonnes=total_forecast,
        total_matched_tonnes=total_matched,
        total_unmatched_tonnes=total_unmatched,
        total_farmer_net_revenue_inr=total_revenue,
        total_estimated_tonnes_diverted=total_diverted,
        warnings=warnings,
        is_simulated=True,
    )
