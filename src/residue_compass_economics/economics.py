"""
Deterministic Economic Decision Engine for Residue Compass Part 4.
Evaluates KEEP vs. SELL vs. FEED on a strictly consistent net INR/tonne basis.
Calculates exact break-even buyer offers, price bands, and explainability narratives.
"""

from typing import Dict, Any, Optional, Tuple
from residue_compass_economics.config import EconomicsConfig
from residue_compass_economics.schemas import (
    VillageStrawForecast,
    VillageEconomicInput,
    EconomicDecision,
    WhatIfResult,
)
from residue_compass_economics.exceptions import ValidationError, CalculationError


def calculate_nutrient_replacement_value_per_tonne(config: EconomicsConfig) -> Tuple[float, Dict[str, float]]:
    """
    Computes monetary value of retained macro-nutrients (N, P, K, S) in 1 metric tonne of paddy straw
    based on subsidized active fertilizer equivalent prices.
    """
    n_val = config.nitrogen_kg_per_tonne * config.urea_n_price_inr_per_kg
    p_val = config.phosphorus_kg_per_tonne * config.dap_p_price_inr_per_kg
    k_val = config.potassium_kg_per_tonne * config.mop_k_price_inr_per_kg
    s_val = config.sulfur_kg_per_tonne * config.sulfur_price_inr_per_kg
    total_nutrient_val = n_val + p_val + k_val + s_val
    breakdown = {
        "nitrogen_val_inr": round(n_val, 2),
        "phosphorus_val_inr": round(p_val, 2),
        "potassium_val_inr": round(k_val, 2),
        "sulfur_val_inr": round(s_val, 2),
        "total_nutrient_val_inr": round(total_nutrient_val, 2),
    }
    return total_nutrient_val, breakdown


def calculate_keep_value(
    config: EconomicsConfig,
    custom_insitu_cost: Optional[float] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    Evaluates net comparative value of keeping straw on-farm (in-situ mulching/incorporation).
    Net Keep = (Nutrient Value + Soil Organic/Moisture Benefit) - Machine Pass/Mulching Cost.
    """
    nutrient_val, nutrient_breakdown = calculate_nutrient_replacement_value_per_tonne(config)
    soil_benefit = config.soil_organic_matter_benefit_inr_per_tonne
    gross_benefit = nutrient_val + soil_benefit

    insitu_cost = custom_insitu_cost if custom_insitu_cost is not None else config.insitu_management_cost_inr_per_tonne
    if insitu_cost < 0:
        raise ValidationError("In-situ mulching cost cannot be negative.", field="insitu_cost")

    net_keep = gross_benefit - insitu_cost
    details = {
        "gross_keep_benefit_inr_per_tonne": round(gross_benefit, 2),
        "insitu_mulching_cost_inr_per_tonne": round(insitu_cost, 2),
        "soil_benefit_inr_per_tonne": round(soil_benefit, 2),
        "nutrient_breakdown": nutrient_breakdown,
        "net_keep_value_inr_per_tonne": round(net_keep, 2),
    }
    return net_keep, details


def calculate_feed_value(
    config: EconomicsConfig,
    custom_fodder_value: Optional[float] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    Evaluates net comparative value of using straw as animal feed / dry fodder.
    Net Feed = Local Fodder Value - (Chopping/Urea-treatment Cost + Local Handling Cost).
    """
    fodder_val = custom_fodder_value if custom_fodder_value is not None else config.default_fodder_market_value_inr_per_tonne
    if fodder_val < 0:
        raise ValidationError("Fodder market value cannot be negative.", field="fodder_value")

    prep_cost = config.feed_preparation_and_urea_treatment_cost_inr_per_tonne
    handling_cost = config.feed_local_handling_cost_inr_per_tonne
    total_costs = prep_cost + handling_cost

    net_feed = fodder_val - total_costs
    details = {
        "gross_fodder_value_inr_per_tonne": round(fodder_val, 2),
        "feed_preparation_cost_inr_per_tonne": round(prep_cost, 2),
        "feed_handling_cost_inr_per_tonne": round(handling_cost, 2),
        "total_feed_costs_inr_per_tonne": round(total_costs, 2),
        "net_feed_value_inr_per_tonne": round(net_feed, 2),
    }
    return net_feed, details


def calculate_seller_collection_costs(
    distance_km: float,
    config: EconomicsConfig,
    custom_baling_cost: Optional[float] = None,
    buyer_covers_transport: bool = False,
    buyer_covers_baling: bool = False,
) -> Tuple[float, Dict[str, float]]:
    """
    Computes per-tonne collection, baling, loading, and transport costs borne by the seller.
    """
    if distance_km < 0:
        raise ValidationError("Distance cannot be negative.", field="distance_km")

    # Baling
    if buyer_covers_baling:
        baling_cost = 0.0
    else:
        baling_cost = custom_baling_cost if custom_baling_cost is not None else config.default_baling_cost_inr_per_tonne

    # Loading
    loading_cost = config.default_fixed_loading_cost_inr_per_tonne

    # Transport
    if buyer_covers_transport:
        transport_cost = 0.0
    else:
        transport_cost = distance_km * config.default_transport_cost_per_tonne_km_inr

    total_seller_costs = baling_cost + loading_cost + transport_cost
    breakdown = {
        "baling_cost_inr_per_tonne": round(baling_cost, 2),
        "loading_cost_inr_per_tonne": round(loading_cost, 2),
        "transport_cost_inr_per_tonne": round(transport_cost, 2),
        "total_seller_collection_costs_inr_per_tonne": round(total_seller_costs, 2),
    }
    return total_seller_costs, breakdown


def evaluate_village_economics(
    forecast: VillageStrawForecast,
    economic_input: Optional[VillageEconomicInput] = None,
    config: Optional[EconomicsConfig] = None,
) -> EconomicDecision:
    """
    Evaluates net comparative value across KEEP, SELL, and FEED options for a village.
    Produces deterministic recommendations, break-even prices, and human-readable explainability.
    """
    cfg = config or EconomicsConfig()
    econ = economic_input or VillageEconomicInput(village_id=forecast.village_id)

    # 1. Evaluate KEEP
    net_keep, keep_details = calculate_keep_value(
        config=cfg,
        custom_insitu_cost=econ.custom_insitu_cost_inr_per_tonne,
    )

    # 2. Evaluate FEED
    net_feed, feed_details = calculate_feed_value(
        config=cfg,
        custom_fodder_value=econ.local_fodder_value_inr_per_tonne,
    )

    # 3. Best non-sell baseline
    best_non_sell_value = max(net_keep, net_feed)

    # 4. Collection costs for SELL
    distance_km = econ.buyer_distance_km if econ.buyer_distance_km is not None else 15.0  # nominal default
    seller_costs, cost_breakdown = calculate_seller_collection_costs(
        distance_km=distance_km,
        config=cfg,
        custom_baling_cost=econ.custom_baling_cost_inr_per_tonne,
        buyer_covers_transport=econ.buyer_covers_transport,
        buyer_covers_baling=econ.buyer_covers_baling,
    )

    # 5. Break-Even Price
    # Minimum buyer offer where Net Sell >= best non-sell alternative
    # Offer - seller_costs = best_non_sell_value  =>  Offer = best_non_sell_value + seller_costs
    break_even_price = best_non_sell_value + seller_costs

    # 6. Recommended Price Band
    recommended_price_low = round(break_even_price * cfg.recommended_price_low_margin_ratio, 2)
    recommended_price_high = round(break_even_price * cfg.recommended_price_high_margin_ratio, 2)

    # 7. Evaluate SELL if offer is provided
    if econ.offered_straw_price_inr_per_tonne is not None:
        net_sell = econ.offered_straw_price_inr_per_tonne - seller_costs
    else:
        # If no buyer offer exists yet, benchmark against break-even (net_sell = best_non_sell_value)
        net_sell = 0.0

    # 8. Determine Best Choice
    options = {
        "keep": net_keep,
        "feed": net_feed,
    }
    if econ.offered_straw_price_inr_per_tonne is not None:
        options["sell"] = net_sell

    # Deterministic choice resolution
    # Order of priority on exact numerical ties: sell > keep > feed (incentivizing active logistics)
    best_choice = max(options, key=lambda k: (options[k], 1 if k == "sell" else (0 if k == "keep" else -1)))

    # 9. Explanation Narrative
    explanation_lines = []
    if best_choice == "sell":
        margin = net_sell - best_non_sell_value
        explanation_lines.append(
            f"SELL is recommended: Buyer offer of INR {econ.offered_straw_price_inr_per_tonne:.2f}/t "
            f"yields net revenue of INR {net_sell:.2f}/t after deducting INR {seller_costs:.2f}/t collection costs. "
            f"This exceeds the best on-farm alternative by INR {margin:.2f}/t."
        )
    elif best_choice == "feed":
        explanation_lines.append(
            f"FEED is recommended: Local fodder net return of INR {net_feed:.2f}/t outperforms "
            f"retention/mulching (INR {net_keep:.2f}/t)"
            + (f" and selling net return (INR {net_sell:.2f}/t)." if econ.offered_straw_price_inr_per_tonne else ".")
        )
    else:  # keep
        explanation_lines.append(
            f"KEEP is recommended: On-farm soil nutrient & moisture retention yields net agronomic value "
            f"of INR {net_keep:.2f}/t (gross nutrient/carbon value INR {keep_details['gross_keep_benefit_inr_per_tonne']:.2f}/t "
            f"minus INR {keep_details['insitu_mulching_cost_inr_per_tonne']:.2f}/t incorporation cost)."
            + (f" Current buyer offer gives only net INR {net_sell:.2f}/t (break-even is INR {break_even_price:.2f}/t)."
               if econ.offered_straw_price_inr_per_tonne else f" Break-even selling price required is INR {break_even_price:.2f}/t.")
        )

    if all(val < 0 for val in options.values()):
        explanation_lines.append(
            "Note: All evaluated alternatives yield negative net returns under current parameters; "
            f"'{best_choice}' minimizes total financial loss."
        )

    explanation = " ".join(explanation_lines)

    assumptions = {
        "economics_config": cfg.to_dict(),
        "keep_details": keep_details,
        "feed_details": feed_details,
        "cost_breakdown": cost_breakdown,
        "assumed_distance_km": distance_km,
        "best_non_sell_baseline": "keep" if net_keep >= net_feed else "feed",
        "best_non_sell_value_inr": round(best_non_sell_value, 2),
    }

    return EconomicDecision(
        village_id=forecast.village_id,
        best_choice=best_choice,  # type: ignore
        break_even_price_inr_per_tonne=round(break_even_price, 2),
        recommended_price_low_inr_per_tonne=recommended_price_low,
        recommended_price_high_inr_per_tonne=recommended_price_high,
        net_keep_value_inr_per_tonne=round(net_keep, 2),
        net_sell_value_inr_per_tonne=round(net_sell, 2),
        net_feed_value_inr_per_tonne=round(net_feed, 2),
        currency="INR",
        assumptions=assumptions,
        explanation=explanation,
        is_simulated=forecast.is_simulated,
    )


def execute_what_if_analysis(
    base_forecast: VillageStrawForecast,
    base_input: VillageEconomicInput,
    overrides: Dict[str, Any],
    config: Optional[EconomicsConfig] = None,
) -> WhatIfResult:
    """
    Applies overrides to assumptions or market parameters and recalculates decision.
    Produces clear before-and-after diff.
    """
    cfg = config or EconomicsConfig()
    baseline_decision = evaluate_village_economics(base_forecast, base_input, cfg)

    # Clone and mutate config or economic input
    updated_cfg_dict = cfg.to_dict()
    updated_input_dict = base_input.to_dict()

    for k, v in overrides.items():
        if k in updated_cfg_dict:
            updated_cfg_dict[k] = v
        elif k in updated_input_dict:
            updated_input_dict[k] = v
        elif k == "offered_price":
            updated_input_dict["offered_straw_price_inr_per_tonne"] = v
        elif k == "distance_km":
            updated_input_dict["buyer_distance_km"] = v
        elif k == "baling_cost":
            updated_input_dict["custom_baling_cost_inr_per_tonne"] = v
        elif k == "fodder_value":
            updated_input_dict["local_fodder_value_inr_per_tonne"] = v
        else:
            # Dynamic config override
            updated_cfg_dict[k] = v

    new_cfg = EconomicsConfig.from_dict(updated_cfg_dict)
    new_input = VillageEconomicInput.from_dict(updated_input_dict)

    updated_decision = evaluate_village_economics(base_forecast, new_input, new_cfg)

    # Compute diff
    changed_fields = {}
    if baseline_decision.best_choice != updated_decision.best_choice:
        changed_fields["best_choice"] = {
            "from": baseline_decision.best_choice,
            "to": updated_decision.best_choice,
        }
    for field_name in [
        "break_even_price_inr_per_tonne",
        "net_keep_value_inr_per_tonne",
        "net_sell_value_inr_per_tonne",
        "net_feed_value_inr_per_tonne",
    ]:
        old_val = getattr(baseline_decision, field_name)
        new_val = getattr(updated_decision, field_name)
        if round(old_val, 2) != round(new_val, 2):
            changed_fields[field_name] = {
                "from": old_val,
                "to": new_val,
                "delta": round(new_val - old_val, 2),
            }

    explanation = (
        f"What-If applied {len(overrides)} parameter overrides. "
        f"Recommendation moved from '{baseline_decision.best_choice}' to '{updated_decision.best_choice}'."
        if baseline_decision.best_choice != updated_decision.best_choice
        else f"Recommendation remained '{baseline_decision.best_choice}'. Break-even changed by INR "
        f"{updated_decision.break_even_price_inr_per_tonne - baseline_decision.break_even_price_inr_per_tonne:.2f}/t."
    )

    return WhatIfResult(
        village_id=base_forecast.village_id,
        baseline_decision=baseline_decision,
        updated_decision=updated_decision,
        applied_overrides=overrides,
        changed_fields=changed_fields,
        explanation=explanation,
    )
