"""Fix decisions router – removed dangling Depends() usage outside FastAPI context."""
from typing import Optional

from fastapi import APIRouter, Body

from app.core.deps import FarmerUser
from app.core.errors import forbidden, not_found
from app.schemas.decision import Decision
from app.services import queries

router = APIRouter(tags=["decision"])


@router.get("/villages/{village_id}/decision", response_model=Decision)
def get_decision(
    village_id: str,
    _user: FarmerUser,
):
    # Farmers can only see their own village's data
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
    assumptions: dict = Body(
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
    """
    if _user.get("role") == "farmer" and _user.get("village_id") != village_id:
        raise forbidden()
    base = queries.get_decision(village_id)
    if base is None:
        raise not_found("decision", "village_id")

    merged = {**base["assumptions"], **assumptions}
    baling    = float(merged.get("baling_cost_per_tonne", 450))
    transport = float(merged.get("transport_cost_per_tonne_per_km", 12))
    dist      = float(merged.get("distance_km", 38))
    fert      = float(merged.get("fertilizer_value_per_tonne", 640))

    total_cost = baling + transport * dist
    sell_gain  = float(base["per_tonne_inr"]["sell"]["gain"])

    base["assumptions"]                              = merged
    base["break_even_price_per_tonne_inr"]           = total_cost
    base["per_tonne_inr"]["sell"]["cost"]            = total_cost
    base["per_tonne_inr"]["sell"]["net"]             = sell_gain - total_cost
    base["per_tonne_inr"]["keep"]["gain"]            = fert
    base["per_tonne_inr"]["keep"]["net"]             = fert - float(base["per_tonne_inr"]["keep"]["cost"])
    return base
