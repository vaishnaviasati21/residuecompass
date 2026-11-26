"""
Task runner – single entry point for all background jobs.

When Celery + Redis are available, tasks are dispatched to the queue.
When they're not (demo mode / no Redis), the same logic runs synchronously
in-process so the demo never breaks.
"""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("workers")

# Try to import Celery; set a flag so we know what mode we're in.
try:
    from celery import Celery as _Celery
    _celery_app = _Celery("rc", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
    _celery_app.conf.task_serializer = "json"
    _celery_app.conf.result_serializer = "json"
    _celery_app.conf.timezone = "UTC"
    _celery_app.conf.beat_schedule = {
        "daily-refresh": {
            "task": "app.workers.task_runner.daily_refresh",
            "schedule": 86400,  # every 24 h
        },
    }
    CELERY_AVAILABLE = True
except Exception:
    _celery_app = None
    CELERY_AVAILABLE = False


# ── Synchronous implementations ───────────────────────────────────────────

def _refresh_forecasts(village_id: Optional[str] = None) -> dict:
    """Re-run the ML forecast for one village or all."""
    if settings.DEMO_MODE:
        logger.info("[DEMO] refresh_forecasts – returning seed data unchanged")
        return {"mode": "demo", "villages_refreshed": 0}

    # Production: call ml.predict for each village
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../ml"))
        from predict import predict_village  # type: ignore
        from app.core.db import engine
        from sqlalchemy import text

        from datetime import date, datetime
        import json
        with engine.begin() as conn:
            if village_id:
                vids = [village_id]
            else:
                vids = [r[0] for r in conn.execute(text("SELECT id FROM villages")).all()]

            count = 0
            for vid in vids:
                result = predict_village(vid)
                conn.execute(text("""
                    INSERT INTO forecasts
                    (village_id, season, harvest_expected, harvest_earliest, harvest_latest,
                     paddy_area_ha, straw_expected, straw_low, straw_high, confidence_tag,
                     reasons, model_version, generated_at, harvest_status)
                    VALUES
                    (:vid, :season, :he, :hea, :hl, :area, :se, :sl, :sh, :tag,
                     CAST(:reasons AS jsonb), :mv, :gen, :hs)
                """), {
                    "vid": vid,
                    "season": result["season"],
                    "he": date.fromisoformat(str(result["harvest"]["expected_date"])),
                    "hea": date.fromisoformat(str(result["harvest"]["earliest_date"])),
                    "hl": date.fromisoformat(str(result["harvest"]["latest_date"])),
                    "area": result["straw"]["paddy_area_ha"],
                    "se": result["straw"]["expected_tonnes"],
                    "sl": result["straw"]["low_tonnes"],
                    "sh": result["straw"]["high_tonnes"],
                    "tag": result["confidence"]["tag"],
                    "reasons": json.dumps(result["confidence"].get("reasons", [])),
                    "mv": result.get("model_version", "ml-1.0"),
                    "gen": datetime.fromisoformat(str(result["generated_at"]).replace("Z", "+00:00")),
                    "hs": result.get("harvest_status", "READY_SOON"),
                })
                logger.info("[FORECAST] %s refreshed", vid)
                count += 1
        return {"villages_refreshed": count}
    except ImportError:
        logger.warning("ml.predict not found – using seed data")
        return {"mode": "ml_not_available", "villages_refreshed": 0}


def _run_matching() -> dict:
    """Re-run the economics matcher for all villages."""
    if settings.DEMO_MODE:
        logger.info("[DEMO] run_matching – returning seed matches unchanged")
        return {"mode": "demo", "matches_created": 0}

    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../economics"))
        from match import run_matching  # type: ignore
        from datetime import date, datetime
        from app.core.db import engine
        from sqlalchemy import text
        matches = run_matching()
        with engine.begin() as conn:
            for m in matches:
                conn.execute(text("""
                    INSERT INTO matches
                    (match_id, village_id, buyer_id, baler_id, truck_id, tonnes, pickup_date,
                     price_per_tonne_inr, status, created_at, net_to_farmers_inr)
                    VALUES
                    (:id, :vid, :bid, :bal, :trk, :t, :pd, :price, :st, :ca, :net)
                    ON CONFLICT (match_id) DO UPDATE SET
                        tonnes = EXCLUDED.tonnes,
                        pickup_date = EXCLUDED.pickup_date,
                        price_per_tonne_inr = EXCLUDED.price_per_tonne_inr,
                        net_to_farmers_inr = EXCLUDED.net_to_farmers_inr
                """), {
                    "id": m["match_id"],
                    "vid": m["village_id"],
                    "bid": m["buyer"]["id"],
                    "bal": m["baler"]["id"],
                    "trk": m["truck"]["id"],
                    "t": m["tonnes"],
                    "pd": date.fromisoformat(str(m["pickup_date"])),
                    "price": m["price_per_tonne_inr"],
                    "st": m.get("status", "PROPOSED"),
                    "ca": datetime.fromisoformat(str(m["created_at"]).replace("Z", "+00:00")),
                    "net": m.get("net_to_farmers_inr"),
                })
        return {"matches_created": len(matches)}
    except ImportError:
        logger.warning("economics.match not found – using seed data")
        return {"mode": "matcher_not_available", "matches_created": 0}


def _daily_refresh() -> dict:
    """Combined daily refresh: forecasts + matching + notifications."""
    logger.info("[SCHEDULER] Starting daily refresh")
    r1 = _refresh_forecasts()
    r2 = _run_matching()

    # Send notifications for all CONFIRMED matches that haven't been notified yet
    from app.core.db import engine
    from sqlalchemy import text
    from app.notifier.sender import send_notification_for_match

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT m.match_id FROM matches m
            WHERE m.status = 'CONFIRMED'
              AND NOT EXISTS (
                  SELECT 1 FROM notifications n WHERE n.match_id = m.match_id
              )
        """)).all()

    notif_count = 0
    for (mid,) in rows:
        notif_count += send_notification_for_match(mid)

    return {**r1, **r2, "notifications_sent": notif_count}


# ── Celery task wrappers (registered only when Celery is available) ───────

if CELERY_AVAILABLE and _celery_app:
    @_celery_app.task(name="app.workers.task_runner.refresh_forecasts")
    def celery_refresh_forecasts(village_id=None):
        return _refresh_forecasts(village_id)

    @_celery_app.task(name="app.workers.task_runner.run_matching")
    def celery_run_matching():
        return _run_matching()

    @_celery_app.task(name="app.workers.task_runner.daily_refresh")
    def celery_daily_refresh():
        return _daily_refresh()


# ── Public entry point ────────────────────────────────────────────────────

_JOB_MAP = {
    "refresh_forecasts": _refresh_forecasts,
    "run_matching": _run_matching,
    "daily_refresh": _daily_refresh,
}


def run(job: str, village_id: Optional[str] = None) -> tuple[dict | None, str | None]:
    """
    Dispatch a job. Returns (result_dict, error_string).

    If Celery is available and DEMO_MODE is off, enqueues async.
    Otherwise runs synchronously for reliability.
    """
    fn = _JOB_MAP.get(job)
    if fn is None:
        return None, f"Unknown job: {job}"

    try:
        if CELERY_AVAILABLE and not settings.DEMO_MODE:
            # Fire-and-forget; result stored in Redis
            if job == "refresh_forecasts":
                celery_refresh_forecasts.delay(village_id)
            elif job == "run_matching":
                celery_run_matching.delay()
            elif job == "daily_refresh":
                celery_daily_refresh.delay()
            return {"queued": True, "job": job}, None
        else:
            kwargs = {"village_id": village_id} if job == "refresh_forecasts" else {}
            result = fn(**kwargs)
            return result, None
    except Exception as exc:
        logger.exception("Job %s failed: %s", job, exc)
        return None, str(exc)
