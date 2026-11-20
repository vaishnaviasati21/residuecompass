"""
Offline End-to-End Demo for Residue Compass Part 4: Economics, Matching, and Validation.
Runnable with zero external dependencies:
    python examples/run_demo.py
"""

import sys
import json
from pathlib import Path

# Ensure src is on path
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
OUTPUTS_DIR = ROOT_DIR / "outputs"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

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


def run_demo():
    print("=" * 80)
    print(" RESIDUE COMPASS — PART 4: ECONOMICS, MATCHING & VALIDATION DEMO")
    print(" (Zero External Dependencies | 100% Deterministic | Fully Offline)")
    print("=" * 80)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load Synthetic Benchmark Entities
    print("\n[Step 1] Loading Synthetic Benchmark Datasets...")
    forecasts = get_sample_forecasts()
    econ_inputs = get_sample_economic_inputs()
    buyers = get_sample_buyers()
    balers = get_sample_balers()
    trucks = get_sample_trucks()

    print(f"  * Villages loaded: {len(forecasts)}")
    print(f"  * Buyers loaded:   {len(buyers)}")
    print(f"  * Balers loaded:   {len(balers)}")
    print(f"  * Trucks loaded:   {len(trucks)}")

    # 2. Structural & Capacity Validation
    print("\n[Step 2] Validating Project Data & Contract Integrity...")
    val_res = validate_project_data(forecasts, buyers, balers, trucks)
    if val_res.is_valid:
        print("  ✓ All data contracts, date windows, capacities, and coordinates are VALID.")
    else:
        print(f"  ✗ Validation Errors: {val_res.errors}")
        return

    # 3. Economic Decisions across Villages
    print("\n[Step 3] Computing Comparative Economic Decisions (KEEP vs. SELL vs. FEED)...")
    decisions = {}
    for f in forecasts:
        inp = econ_inputs.get(f.village_id)
        decision = calculate_decision(f, inp)
        decisions[f.village_id] = decision
        print(f"\n  ► Village {f.village_id} ({f.village_name or 'Cluster'}):")
        print(f"      Straw Forecast:       {f.straw_tonnes_expected:.1f} tonnes ({f.confidence} confidence)")
        print(f"      Best Choice:          {decision.best_choice.upper()}")
        print(f"      Break-Even Offer:     INR {decision.break_even_price_inr_per_tonne:,.2f}/t")
        print(f"      Recommended Price:    INR {decision.recommended_price_low_inr_per_tonne:,.2f} - {decision.recommended_price_high_inr_per_tonne:,.2f}/t")
        print(f"      Net KEEP Value:       INR {decision.net_keep_value_inr_per_tonne:,.2f}/t")
        print(f"      Net SELL Value:       INR {decision.net_sell_value_inr_per_tonne:,.2f}/t")
        print(f"      Net FEED Value:       INR {decision.net_feed_value_inr_per_tonne:,.2f}/t")
        print(f"      Rationale:            {decision.explanation}")

    # 4. What-If Analysis
    print("\n[Step 4] Running What-If Analysis (Sensitivity to Price & Fuel Shocks)...")
    vil1_forecast = forecasts[0]
    vil1_input = econ_inputs["VIL-001"]
    overrides = {
        "diesel_price_inr_per_litre": 115.0,
        "offered_price": 1400.0,
    }
    whatif_res = run_what_if(vil1_forecast, vil1_input, overrides)
    print(f"  ► Scenario: Diesel price jumps to INR 115/L and Buyer Offer drops to INR 1,400/t")
    print(f"      Baseline Choice:      {whatif_res.baseline_decision.best_choice.upper()}")
    print(f"      Updated Choice:       {whatif_res.updated_decision.best_choice.upper()}")
    print(f"      Changed Fields:       {json.dumps(whatif_res.changed_fields, indent=6)}")
    print(f"      Analysis:             {whatif_res.explanation}")

    # 5. Matching Engine
    print("\n[Step 5] Running Spatio-Temporal Matching Engine (12 Operational Constraints)...")
    matching_result = run_matching(forecasts, buyers, balers, trucks)
    print(f"  * Generated Bookings:     {len(matching_result.bookings)}")
    print(f"  * Total Forecast Supply:  {matching_result.total_forecast_tonnes:,.1f} tonnes")
    print(f"  * Total Matched Straw:    {matching_result.total_matched_tonnes:,.1f} tonnes")
    print(f"  * Total Unmatched Supply: {matching_result.total_unmatched_tonnes:,.1f} tonnes")
    print(f"  * Farmer Net Revenue:     INR {matching_result.total_farmer_net_revenue_inr:,.2f}")

    print("\n  Confirmed Dispatch Bookings:")
    for b in matching_result.bookings:
        print(f"    - Booking {b.match_id}:")
        print(f"        Village: {b.village_id} -> Buyer: {b.buyer_id} | Pickup Date: {b.pickup_date}")
        print(f"        Matched Volume: {b.matched_tonnes:.1f}t @ INR {b.price_inr_per_tonne:.2f}/t")
        print(f"        Baler: {b.baler_id} | Truck: {b.truck_id} | Road Proxy Dist: {b.transport_distance_km:.1f} km")
        print(f"        Total Logistics Cost: INR {b.total_cost_inr:,.2f}")
        print(f"        Farmer Net Revenue:   INR {b.estimated_farmer_net_revenue_inr:,.2f}")

    if matching_result.unmatched_villages:
        print("\n  Unmatched / Partially Fulfilled Villages:")
        for u in matching_result.unmatched_villages:
            print(f"    - {u.village_id}: {u.remaining_unmatched_tonnes:.1f}t remaining. Reason: {u.reason}")

    # 6. Environmental & Financial Impact
    print("\n[Step 6] Estimating Verifiable Impact Metrics...")
    impact = calculate_impact(forecasts, matching_result.bookings)
    print(f"  * Diverted from Burning:  {impact.estimated_tonnes_diverted:,.1f} metric tonnes (estimated contracted)")
    print(f"  * Allocation Fraction:    {impact.matched_fraction * 100:.1f}%")
    print(f"  * Farmer Net Income:      INR {impact.estimated_farmer_net_revenue_inr:,.2f}")
    print(f"  * Savings vs. Burning:    INR {impact.estimated_farmer_savings_vs_burning_inr:,.2f}")
    print(f"  * Transparency Statement: {impact.confidence_and_limitations}")

    # 7. Multi-Scenario Stress Testing
    print("\n[Step 7] Executing Robustness Stress Testing Suite...")
    stress_report = run_stress_tests(forecasts[0], econ_inputs["VIL-001"])
    print(f"  ► Stress Report for {stress_report.village_id}:")
    print(f"  {'Scenario':<42} | {'Choice':<8} | {'Break-Even':<12} | {'Delta BE':<10}")
    print("  " + "-" * 78)
    for o in stress_report.outcomes:
        switched = " [FLIP]" if o.choice_changed else ""
        print(f"  {o.name:<42} | {o.scenario_choice.upper() + switched:<8} | INR {o.scenario_break_even_price:,.2f} | {o.delta_break_even_price:+,.2f}")

    print(f"\n  Stress Summary: {stress_report.summary_insight}")

    # 8. Save Artifact Outputs
    print("\n[Step 8] Exporting Machine-Readable JSON Outputs...")
    outputs = {
        "decisions": {k: v.to_dict() for k, v in decisions.items()},
        "matching": matching_result.to_dict(),
        "impact": impact.to_dict(),
        "stress_testing": stress_report.to_dict(),
    }

    with open(OUTPUTS_DIR / "demo_decisions.json", "w", encoding="utf-8") as f:
        json.dump(outputs["decisions"], f, indent=2)
    with open(OUTPUTS_DIR / "demo_matches.json", "w", encoding="utf-8") as f:
        json.dump(outputs["matching"], f, indent=2)
    with open(OUTPUTS_DIR / "demo_impact.json", "w", encoding="utf-8") as f:
        json.dump(outputs["impact"], f, indent=2)
    with open(OUTPUTS_DIR / "demo_stress_report.json", "w", encoding="utf-8") as f:
        json.dump(outputs["stress_testing"], f, indent=2)

    print(f"  ✓ Exported outputs to '{OUTPUTS_DIR.resolve()}'")
    print("\n" + "=" * 80)
    print(" DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
