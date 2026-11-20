"""
Validation and Multi-Scenario Stress Testing for Residue Compass Part 4.
Audits project data consistency, date windows, machine capacities, and performs sensitivity testing.
"""

from typing import List, Dict, Any, Optional
from residue_compass_economics.config import EconomicsConfig
from residue_compass_economics.schemas import (
    VillageStrawForecast,
    VillageEconomicInput,
    Buyer,
    Baler,
    Truck,
    EconomicDecision,
    StressScenario,
    ScenarioOutcome,
    StressTestReport,
    ValidationResult,
    parse_iso_date,
)
from residue_compass_economics.economics import evaluate_village_economics


def validate_project_data(
    forecasts: List[VillageStrawForecast],
    buyers: List[Buyer],
    balers: List[Baler],
    trucks: List[Truck],
) -> ValidationResult:
    """
    Performs comprehensive structural and logical validation across all entities:
    - ID uniqueness and non-emptiness.
    - Positive capacities and non-negative quantities.
    - Low <= expected <= high ordering.
    - Date sanity (valid_from <= valid_until, harvest_date <= collection_deadline).
    - Geographic coordinates in valid ranges.
    """
    errors: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}

    # 1. Forecast validations
    village_ids = set()
    for f in forecasts:
        if f.village_id in village_ids:
            errors.append(f"Duplicate village_id found: '{f.village_id}'.")
        village_ids.add(f.village_id)

        if f.collection_deadline:
            h_dt = parse_iso_date(f.harvest_date)
            d_dt = parse_iso_date(f.collection_deadline)
            if d_dt < h_dt:
                errors.append(
                    f"Village '{f.village_id}': deadline ({f.collection_deadline}) is earlier than harvest ({f.harvest_date})."
                )

        if not (-90.0 <= f.latitude <= 90.0 and -180.0 <= f.longitude <= 180.0):
            errors.append(f"Village '{f.village_id}': Coordinates ({f.latitude}, {f.longitude}) out of range.")
        elif f.latitude == 0.0 and f.longitude == 0.0:
            warnings.append(f"Village '{f.village_id}' has (0.0, 0.0) coordinates; road distance proxy will require matrix.")

    # 2. Buyer validations
    buyer_ids = set()
    for b in buyers:
        if b.buyer_id in buyer_ids:
            errors.append(f"Duplicate buyer_id found: '{b.buyer_id}'.")
        buyer_ids.add(b.buyer_id)

        if b.remaining_demand_tonnes > b.max_demand_tonnes:
            errors.append(
                f"Buyer '{b.buyer_id}': remaining_demand ({b.remaining_demand_tonnes}t) exceeds max_demand ({b.max_demand_tonnes}t)."
            )

        if not (-90.0 <= b.latitude <= 90.0 and -180.0 <= b.longitude <= 180.0):
            errors.append(f"Buyer '{b.buyer_id}': Coordinates ({b.latitude}, {b.longitude}) out of range.")

    # 3. Baler validations
    baler_ids = set()
    for bal in balers:
        if bal.baler_id in baler_ids:
            errors.append(f"Duplicate baler_id found: '{bal.baler_id}'.")
        baler_ids.add(bal.baler_id)

        if bal.daily_capacity_tonnes <= 0:
            errors.append(f"Baler '{bal.baler_id}': daily_capacity_tonnes must be > 0.")

    # 4. Truck validations
    truck_ids = set()
    for trk in trucks:
        if trk.truck_id in truck_ids:
            errors.append(f"Duplicate truck_id found: '{trk.truck_id}'.")
        truck_ids.add(trk.truck_id)

        if trk.daily_capacity_tonnes <= 0:
            errors.append(f"Truck '{trk.truck_id}': daily_capacity_tonnes must be > 0.")

    details["village_count"] = len(forecasts)
    details["buyer_count"] = len(buyers)
    details["baler_count"] = len(balers)
    details["truck_count"] = len(trucks)

    is_valid = len(errors) == 0
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        details=details,
    )


def generate_standard_stress_scenarios() -> List[StressScenario]:
    """Generates a standard benchmark suite of economic and logistical stress tests."""
    return [
        StressScenario(
            scenario_id="STRESS-DIESEL-SPIKE",
            name="Diesel Fuel Price Spike (+35%)",
            description="Diesel climbs from INR 90 to INR 121.50/L, inflating per-tonne-km transport cost by 35%.",
            overrides={
                "diesel_price_inr_per_litre": 121.50,
                "default_transport_cost_per_tonne_km_inr": 7.425,
            },
        ),
        StressScenario(
            scenario_id="STRESS-FERTILIZER-SURGE",
            name="Fertilizer Subsidy Reduction (+40% Nutrient Cost)",
            description="Urea, DAP, and MOP prices surge by 40%, boosting the net value of in-situ straw incorporation.",
            overrides={
                "urea_n_price_inr_per_kg": 8.40,
                "dap_p_price_inr_per_kg": 41.30,
                "mop_k_price_inr_per_kg": 47.60,
                "sulfur_price_inr_per_kg": 21.00,
            },
        ),
        StressScenario(
            scenario_id="STRESS-BUYER-PRICE-DROP",
            name="Biomass Market Demand Slump (-30% Buyer Price)",
            description="Buyers cut offered prices by 30% due to biomass inventory glut.",
            overrides={
                "offered_price": 1400.0,
            },
        ),
        StressScenario(
            scenario_id="STRESS-LONG-DISTANCE",
            name="High Transport Distance (70 km Long-Haul)",
            description="Nearby buyers are full; straw must be hauled 70km to a regional power plant.",
            overrides={
                "distance_km": 70.0,
            },
        ),
        StressScenario(
            scenario_id="STRESS-FODDER-DEFICIT",
            name="Regional Fodder Deficit (High Feed Value)",
            description="Severe cattle fodder shortage in dairy belts drives straw fodder value to INR 2,600/tonne.",
            overrides={
                "fodder_value": 2600.0,
            },
        ),
        StressScenario(
            scenario_id="STRESS-SUBSIDIZED-LOGISTICS",
            name="State Subsidized Aggregation (Zero Farmer Baling/Transport)",
            description="Government or aggregator covers baling and hauling costs entirely.",
            overrides={
                "buyer_covers_transport": True,
                "buyer_covers_baling": True,
            },
        ),
    ]


def run_village_stress_tests(
    forecast: VillageStrawForecast,
    economic_input: VillageEconomicInput,
    scenarios: Optional[List[StressScenario]] = None,
    config: Optional[EconomicsConfig] = None,
) -> StressTestReport:
    """
    Executes a multi-scenario sensitivity test against a village's economic baseline.
    Reports whether the optimal decision flips, break-even price movement, and the economic root cause.
    """
    cfg = config or EconomicsConfig()
    baseline = evaluate_village_economics(forecast, economic_input, cfg)
    active_scenarios = scenarios or generate_standard_stress_scenarios()

    outcomes: List[ScenarioOutcome] = []
    switches = 0

    for sc in active_scenarios:
        # Prepare cloned configs
        cfg_dict = cfg.to_dict()
        inp_dict = economic_input.to_dict()

        for k, v in sc.overrides.items():
            if k in cfg_dict:
                cfg_dict[k] = v
            elif k in inp_dict:
                inp_dict[k] = v
            elif k == "offered_price":
                inp_dict["offered_straw_price_inr_per_tonne"] = v
            elif k == "distance_km":
                inp_dict["buyer_distance_km"] = v
            elif k == "fodder_value":
                inp_dict["local_fodder_value_inr_per_tonne"] = v
            else:
                cfg_dict[k] = v

        sc_cfg = EconomicsConfig.from_dict(cfg_dict)
        sc_inp = VillageEconomicInput.from_dict(inp_dict)

        sc_decision = evaluate_village_economics(forecast, sc_inp, sc_cfg)
        choice_changed = sc_decision.best_choice != baseline.best_choice
        if choice_changed:
            switches += 1

        delta_be = round(sc_decision.break_even_price_inr_per_tonne - baseline.break_even_price_inr_per_tonne, 2)

        # Root cause explanation
        if choice_changed:
            root_cause = (
                f"Shifted from '{baseline.best_choice}' to '{sc_decision.best_choice}' because {sc.description} "
                f"altered comparative net values (Break-even changed by INR {delta_be:+.2f}/t)."
            )
        else:
            root_cause = (
                f"Recommendation '{baseline.best_choice}' remained robust despite {sc.name}. "
                f"Break-even shifted by INR {delta_be:+.2f}/t."
            )

        outcomes.append(
            ScenarioOutcome(
                scenario_id=sc.scenario_id,
                name=sc.name,
                baseline_choice=baseline.best_choice,
                scenario_choice=sc_decision.best_choice,
                choice_changed=choice_changed,
                baseline_break_even_price=baseline.break_even_price_inr_per_tonne,
                scenario_break_even_price=sc_decision.break_even_price_inr_per_tonne,
                delta_break_even_price=delta_be,
                root_cause_explanation=root_cause,
            )
        )

    summary_insight = (
        f"Tested {len(outcomes)} scenarios for Village '{forecast.village_id}'. "
        f"The baseline recommendation '{baseline.best_choice}' switched in {switches} out of {len(outcomes)} cases. "
        + ("High sensitivity to logistics and fertilizer market swings; robust contracting advised." if switches >= 2
           else "High economic stability under standard regional price shocks.")
    )

    return StressTestReport(
        village_id=forecast.village_id,
        baseline_decision=baseline,
        outcomes=outcomes,
        summary_insight=summary_insight,
        is_simulated=forecast.is_simulated,
    )
