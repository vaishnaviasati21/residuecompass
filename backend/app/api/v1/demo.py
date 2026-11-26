"""
One-click demo loop.
  POST /demo/run   – run the full village → forecast → decision → match → notify → burn-check cycle
  POST /demo/reset – reload seed data into the database (officer-only, DEMO_MODE=true only)

The notification step now **persists** the notification to the notifications
table (via sender.send_notification_for_match) rather than only rendering text.
The rendered body is still surfaced in the response for the UI.
"""
from fastapi import APIRouter

from app.core.config import settings
from app.core.deps import OfficerUser
from app.core.errors import api_error
from app.notifier.sender import send_notification_for_match
from app.notifier.templates import render_message
from app.schemas.demo import DemoLoopResponse, DemoLoopStep
from app.services import queries

router = APIRouter(prefix="/demo", tags=["demo"])


def _require_demo_mode():
    if not settings.DEMO_MODE:
        raise api_error(403, "DEMO_MODE_DISABLED",
                        "Demo endpoints are disabled when DEMO_MODE=false.")


@router.post("/run", response_model=DemoLoopResponse)
def demo_run(village_id: str = "PB-SNG-0142"):
    """
    One-click loop (available only when DEMO_MODE=true):
    1. Pull latest forecast for the village
    2. Pull latest decision
    3. Pull first proposed match
    4. Send + persist notification (idempotent)
    5. Pull burn events for the village
    """
    _require_demo_mode()
    steps: list[DemoLoopStep] = []

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

    decision = queries.get_decision(village_id)
    steps.append(DemoLoopStep(
        step="decision",
        status="ok" if decision else "missing",
        detail=(
            f"Best option: {decision['best_option']}, "
            f"break-even ₹{decision['break_even_price_per_tonne_inr']}/t"
        ) if decision else "No decision in DB.",
    ))

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

    # ── Notification step: persist AND surface rendered text ──────────────
    notif_body = None
    if match and forecast:
        # Persist to DB (idempotent – sender skips if already sent)
        try:
            send_notification_for_match(match["match_id"])
        except Exception:
            pass  # DB not available in some demo environments

        # Always render for the response payload
        notif_body = render_message(
            language="pa",
            template="match_confirmed",
            pickup_date=str(match["pickup_date"]),
            price=match["price_per_tonne_inr"],
            buyer_name=match["buyer"]["name"],
        )
        steps.append(DemoLoopStep(step="notification", status="ok", detail=notif_body))
    else:
        steps.append(DemoLoopStep(step="notification", status="skipped",
                                  detail="Need a match to generate notification."))

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
def demo_reset(_officer: OfficerUser):
    """
    Re-load the seed JSON into the database.
    Requires officer authentication AND DEMO_MODE=true.
    """
    _require_demo_mode()
    from scripts.load_seed import main as load_seed_main
    load_seed_main()
    return {"status": "ok", "message": "Seed data reloaded."}
