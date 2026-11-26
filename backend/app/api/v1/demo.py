"""
One-click demo loop.
  POST /demo/run   – run the full village → forecast → decision → match → notify → burn-check cycle
  GET  /demo/reset – reload seed data into the database

No auth required so the demo PC can run this without logging in.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.schemas.demo import DemoLoopResponse, DemoLoopStep
from app.services import queries
from app.notifier.templates import render_message

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/run", response_model=DemoLoopResponse)
def demo_run(
    village_id: str = "PB-SNG-0142",
    db: Session = Depends(get_db),
):
    """
    One-click loop:
    1. Pull latest forecast for the village
    2. Pull latest decision
    3. Pull first proposed match
    4. Generate a notification message
    5. Pull burn events for the village
    Returns a summary of every step so the presenter can walk through it.
    """
    steps: list[DemoLoopStep] = []

    # Step 1 – Forecast
    forecast = queries.get_forecast(village_id)
    steps.append(DemoLoopStep(
        step="forecast",
        status="ok" if forecast else "missing",
        detail=(
            f"Harvest {forecast['harvest']['expected_date']}, "
            f"{forecast['straw']['expected_tonnes']} t, "
            f"{forecast['confidence']['tag']} confidence"
        ) if forecast else "No forecast in DB; run seed first.",
    ))

    # Step 2 – Decision
    decision = queries.get_decision(village_id)
    steps.append(DemoLoopStep(
        step="decision",
        status="ok" if decision else "missing",
        detail=(
            f"Best option: {decision['best_option']}, "
            f"break-even ₹{decision['break_even_price_per_tonne_inr']}/t"
        ) if decision else "No decision in DB.",
    ))

    # Step 3 – Match
    matches = queries.list_matches(status="PROPOSED", village_id=village_id)
    match = matches[0] if matches else None
    steps.append(DemoLoopStep(
        step="match",
        status="ok" if match else "missing",
        detail=(
            f"{match['buyer']['name']} collects {match['tonnes']} t "
            f"on {match['pickup_date']} @ ₹{match['price_per_tonne_inr']}/t"
        ) if match else "No PROPOSED match for this village.",
    ))

    # Step 4 – Notification
    notif_body = None
    if match and forecast:
        notif_body = render_message(
            language="pa",
            template="match_confirmed",
            pickup_date=str(match["pickup_date"]),
            price=match["price_per_tonne_inr"],
            buyer_name=match["buyer"]["name"],
        )
        steps.append(DemoLoopStep(
            step="notification",
            status="ok",
            detail=notif_body,
        ))
    else:
        steps.append(DemoLoopStep(step="notification", status="skipped",
                                  detail="Need a match to generate notification."))

    # Step 5 – Burn check
    burns = queries.list_burn_events(village_id=village_id)
    burn_check = None
    if burns:
        burn_check = burns[0]
        steps.append(DemoLoopStep(
            step="burn_check",
            status="alert",
            detail=f"Burn detected on {burn_check['detected_on']} – confidence {burn_check['confidence']}",
        ))
    else:
        steps.append(DemoLoopStep(step="burn_check", status="clear",
                                  detail="No burn events detected for this village."))

    return DemoLoopResponse(
        village_id=village_id,
        steps=steps,
        forecast_snapshot=forecast,
        decision_snapshot=decision,
        match_snapshot=match,
        notification_body=notif_body,
        burn_check=burn_check,
    )


@router.post("/reset", status_code=202)
def demo_reset(db: Session = Depends(get_db)):
    """Re-load the seed JSON into the database."""
    from scripts.load_seed import main as load_seed_main
    try:
        load_seed_main()
        return {"status": "ok", "message": "Seed data reloaded."}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
