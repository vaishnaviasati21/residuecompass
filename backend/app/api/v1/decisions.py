"""
Decision endpoints.
  GET  /villages/{village_id}/decision  – latest recommendation
  POST /decisions/simulate              – what-if calculator with typed assumptions

The simulate endpoint accepts a typed `SimulateAssumptions` schema with
numeric bounds validated by Pydantic before the request hits business logic.
"""
from fastapi import APIRouter, Body

from app.core.deps import FarmerUser
from app.core.errors import forbidden, not_found
from app.schemas.decision import Decision, SimulateAssumptions
from app.services import queries

router = APIRouter(tags=["decision"])


@router.get("/villages/{village_id}/decision", response_model=Decision)
def get_decision(
    village_id: str,
    _user: FarmerUser,
):
    """Return the latest saved decision for a village (farmer scoped)."""
    if _user.get("role") == "farmer" and _user.get("village_id") != village_id:
        raise forbidden()
    data = queries.get_decision(village_id)
    if data is None:
        raise not_found("decision", "village_id")
    return data


@router.post("/decisions/simulate", response_model=Decision, tags=["decision"])
def simulate_decision(
    village_id: str,
    _user: FarmerUser,
    assumptions: SimulateAssumptions = Body(
        ...,
        examples=[{
            "fertilizer_value_per_tonne": 640,
            "baling_cost_per_tonne": 450,
            "transport_cost_per_tonne_per_km": 12,
            "distance_km": 38,
            "diesel_price_per_litre": 90,
        }],
    ),
):
    """
    What-if calculator.  Takes the saved decision and re-computes economics
    with the caller's custom assumptions.  NOT saved to the database.

    All numeric fields are validated with sensible bounds so invalid values
    return 422 rather than a server error.
    """
    if _user.get("role") == "farmer" and _user.get("village_id") != village_id:
        raise forbidden()
    base = queries.get_decision(village_id)
    if base is None:
        raise not_found("decision", "village_id")

    base_assumptions = base.get("assumptions", {})
    caller = assumptions.model_dump(exclude_none=True)
    merged = {**base_assumptions, **caller}

    baling      = float(merged.get("baling_cost_per_tonne", 450))
    transport   = float(merged.get("transport_cost_per_tonne_per_km", 12))
    dist        = float(merged.get("distance_km", 38))
    fert        = float(merged.get("fertilizer_value_per_tonne", 640))
    base_diesel = float(base_assumptions.get("diesel_price_per_litre", 90)) or 90.0
    diesel      = float(merged.get("diesel_price_per_litre", base_diesel))

    # If diesel price changed without an explicit transport-rate override,
    # scale transport cost proportionally to the diesel price change.
    if (
        "diesel_price_per_litre" in caller
        and "transport_cost_per_tonne_per_km" not in caller
    ):
        transport = round(transport * (diesel / base_diesel), 2)
        merged["transport_cost_per_tonne_per_km"] = transport

    total_cost = round(baling + transport * dist, 2)
    sell_gain  = float(base["per_tonne_inr"]["sell"]["gain"])
    keep_cost  = float(base["per_tonne_inr"]["keep"]["cost"])

    base["assumptions"]                    = merged
    base["break_even_price_per_tonne_inr"] = total_cost
    base["per_tonne_inr"]["sell"]["cost"]  = total_cost
    base["per_tonne_inr"]["sell"]["net"]   = round(sell_gain - total_cost, 2)
    base["per_tonne_inr"]["keep"]["gain"]  = fert
    base["per_tonne_inr"]["keep"]["net"]   = round(fert - keep_cost, 2)

    # Recalculate best_option from updated per-tonne net values
    base["best_option"] = max(
        ("keep", "sell", "feed"),
        key=lambda opt: float(base["per_tonne_inr"][opt]["net"]),
    )

    # Recalculate price range consistently around break-even / sell gain
    base["price_range_inr"] = {
        "low":  round(total_cost, 2),
        "high": round(max(total_cost, sell_gain) * 1.15, 2),
    }
    return base
