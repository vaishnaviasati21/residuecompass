"""
Task runner – single entry point for all background jobs.

When Celery + Redis are available, tasks are dispatched to the queue.
When they're not (demo mode / no Redis), the same logic runs synchronously
in-process so the demo never breaks.

Harvest refresh schedule is configurable via HARVEST_REFRESH_CRON (env/settings).
Default: "0 2 * * *" (2 AM UTC daily).  During harvest season you might use
"0 2 * 10,11 *" (Oct–Nov only).

Production ML/economics providers are detected at dispatch time; a clear
RuntimeError is raised (not a silent warning) when DEMO_MODE=false and the
providers are absent.
"""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("workers")

# ── Celery setup ──────────────────────────────────────────────────────────

CELERY_AVAILABLE = False
_celery_app = None

try:
    from celery import Celery as _Celery           # type: ignore
    from celery.schedules import crontab           # type: ignore

    _celery_app = _Celery(
        "rc",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
    )
    _celery_app.conf.task_serializer   = "json"
    _celery_app.conf.result_serializer = "json"
    _celery_app.conf.timezone          = "UTC"

    # Configurable beat schedule
    _cron_expr = getattr(settings, "HARVEST_REFRESH_CRON", "0 2 * * *")
    try:
        _h, _m, _dom, _mo, _dow = _cron_expr.split()
        _schedule = crontab(
            hour=_h, minute=_m,
            day_of_month=_dom, month_of_year=_mo, day_of_week=_dow,
        )
    except Exception:
        logger.warning(
            "HARVEST_REFRESH_CRON '%s' is invalid; falling back to daily at 02:00 UTC",
            _cron_expr,
        )
        _schedule = crontab(hour=2, minute=0)

    _celery_app.conf.beat_schedule = {
        "daily-refresh": {
            "task":     "app.workers.task_runner.daily_refresh",
            "schedule": _schedule,
        },
    }
    CELERY_AVAILABLE = True
except Exception as _ce:
    logger.info("Celery not available (%s); running in sync mode", _ce)
    _celery_app     = None
    CELERY_AVAILABLE = False


# ── Provider availability guards ──────────────────────────────────────────

def _require_ml() -> None:
    """
    In production, fail loudly if the ML prediction module is missing.
    In demo mode, the check is silently skipped.
    """
    if settings.DEMO_MODE:
        return
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../ml"))
    try:
        import predict  # type: ignore  # noqa: F401
    except ImportError:
        raise RuntimeError(
            "ML provider 'ml/predict.py' is not present. "
            "Cannot run forecast refresh in production without it. "
            "Set DEMO_MODE=true for demo/testing."
        )


def _require_economics() -> None:
    """
    In production, fail loudly if the economics matching module is missing.
    """
    if settings.DEMO_MODE:
        return
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../economics"))
    try:
        import match  # type: ignore  # noqa: F401
    except ImportError:
        raise RuntimeError(
            "Economics provider 'economics/match.py' is not present. "
            "Cannot run match refresh in production without it. "
            "Set DEMO_MODE=true for demo/testing."
        )


# ── Synchronous implementations ───────────────────────────────────────────

def _refresh_forecasts(village_id: Optional[str] = None) -> dict:
    """Re-run the ML forecast for one village or all."""
    if settings.DEMO_MODE:
        logger.info("[DEMO] refresh_forecasts – returning seed data unchanged")
        return {"mode": "demo", "villages_refreshed": 0}

    _require_ml()

    import sys, os, json
    from datetime import date, datetime

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../ml"))
    from predict import predict_village  # type: ignore
    from app.core.db import engine
    from sqlalchemy import text

    with engine.begin() as conn:
        vids = (
            [village_id]
            if village_id
            else [r[0] for r in conn.execute(text("SELECT id FROM villages")).all()]
        )
        count = 0
        for vid in vids:
            result = predict_village(vid)
            conn.execute(
                text("""
                    INSERT INTO forecasts
                        (village_id, season, harvest_expected, harvest_earliest, harvest_latest,
                         paddy_area_ha, straw_expected, straw_low, straw_high, confidence_tag,
                         reasons, model_version, generated_at, harvest_status)
                    VALUES
                        (:vid, :season, :he, :hea, :hl, :area, :se, :sl, :sh, :tag,
                         CAST(:reasons AS jsonb), :mv, :gen, :hs)
                """),
                {
                    "vid":    vid,
                    "season": result["season"],
                    "he":     date.fromisoformat(str(result["harvest"]["expected_date"])),
                    "hea":    date.fromisoformat(str(result["harvest"]["earliest_date"])),
                    "hl":     date.fromisoformat(str(result["harvest"]["latest_date"])),
                    "area":   result["straw"]["paddy_area_ha"],
                    "se":     result["straw"]["expected_tonnes"],
                    "sl":     result["straw"]["low_tonnes"],
                    "sh":     result["straw"]["high_tonnes"],
                    "tag":    result["confidence"]["tag"],
                    "reasons": json.dumps(result["confidence"].get("reasons", [])),
                    "mv":     result.get("model_version", "ml-1.0"),
                    "gen":    datetime.fromisoformat(
                        str(result["generated_at"]).replace("Z", "+00:00")
                    ),
                    "hs":     result.get("harvest_status", "READY_SOON"),
                },
            )
            logger.info("[FORECAST] %s refreshed", vid)
            count += 1

    return {"villages_refreshed": count}


def _run_matching() -> dict:
    """Re-run the economics matcher for all villages."""
    if settings.DEMO_MODE:
        logger.info("[DEMO] run_matching – returning seed matches unchanged")
        return {"mode": "demo", "matches_created": 0}

    _require_economics()

    import sys, os
    from datetime import date, datetime

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../economics"))
    from match import run_matching  # type: ignore
    from app.core.db import engine
    from sqlalchemy import text

    matches = run_matching()
    with engine.begin() as conn:
        for m in matches:
            conn.execute(
                text("""
                    INSERT INTO matches
                        (match_id, village_id, buyer_id, baler_id, truck_id, tonnes, pickup_date,
                         price_per_tonne_inr, status, created_at, net_to_farmers_inr)
                    VALUES
                        (:id, :vid, :bid, :bal, :trk, :t, :pd, :price, :st, :ca, :net)
                    ON CONFLICT (match_id) DO UPDATE SET
                        tonnes              = EXCLUDED.tonnes,
                        pickup_date         = EXCLUDED.pickup_date,
                        price_per_tonne_inr = EXCLUDED.price_per_tonne_inr,
                        net_to_farmers_inr  = EXCLUDED.net_to_farmers_inr
                """),
                {
                    "id":    m["match_id"],
                    "vid":   m["village_id"],
                    "bid":   m["buyer"]["id"],
                    "bal":   m["baler"]["id"],
                    "trk":   m["truck"]["id"],
                    "t":     m["tonnes"],
                    "pd":    date.fromisoformat(str(m["pickup_date"])),
                    "price": m["price_per_tonne_inr"],
                    "st":    m.get("status", "PROPOSED"),
                    "ca":    datetime.fromisoformat(
                        str(m["created_at"]).replace("Z", "+00:00")
                    ),
                    "net":   m.get("net_to_farmers_inr"),
                },
            )
    return {"matches_created": len(matches)}


def _daily_refresh() -> dict:
    """Combined daily refresh: forecasts + matching + notifications."""
    logger.info("[SCHEDULER] Starting daily refresh")
    r1 = _refresh_forecasts()
    r2 = _run_matching()

    # Send notifications for all CONFIRMED matches not yet notified
    from app.core.db import engine
    from sqlalchemy import text
    from app.notifier.sender import send_notification_for_match

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT m.match_id FROM matches m
             WHERE m.status = 'CONFIRMED'
               AND NOT EXISTS (
                   SELECT 1 FROM notifications n
                    WHERE n.match_id = m.match_id AND n.status = 'sent'
               )
        """)).all()

    notif_count = sum(send_notification_for_match(mid) for (mid,) in rows)
    return {**r1, **r2, "notifications_sent": notif_count}


# ── Celery task wrappers ───────────────────────────────────────────────────

if CELERY_AVAILABLE and _celery_app:

    @_celery_app.task(name="app.workers.task_runner.refresh_forecasts", bind=True)
    def celery_refresh_forecasts(self, village_id=None):   # type: ignore
        return _refresh_forecasts(village_id)

    @_celery_app.task(name="app.workers.task_runner.run_matching", bind=True)
    def celery_run_matching(self):                          # type: ignore
        return _run_matching()

    @_celery_app.task(name="app.workers.task_runner.daily_refresh", bind=True)
    def celery_daily_refresh(self):                         # type: ignore
        return _daily_refresh()


# ── Public dispatch ────────────────────────────────────────────────────────

_JOB_MAP = {
    "refresh_forecasts": _refresh_forecasts,
    "run_matching":      _run_matching,
    "daily_refresh":     _daily_refresh,
}


def dispatch_async(job: str, village_id: Optional[str] = None):
    """
    Dispatch a named job to Celery and return the AsyncResult.
    Returns None if the job name is unknown or Celery is not available.
    """
    if not (CELERY_AVAILABLE and _celery_app):
        return None
    if job == "refresh_forecasts":
        return celery_refresh_forecasts.delay(village_id)   # type: ignore
    if job == "run_matching":
        return celery_run_matching.delay()                   # type: ignore
    if job == "daily_refresh":
        return celery_daily_refresh.delay()                  # type: ignore
    return None


def run(job: str, village_id: Optional[str] = None) -> tuple[dict | None, str | None]:
    """
    Dispatch a job synchronously.  Returns (result_dict, error_string).
    Used for demo / sync fallback paths.
    """
    fn = _JOB_MAP.get(job)
    if fn is None:
        return None, f"Unknown job: {job}"
    try:
        kwargs = {"village_id": village_id} if job == "refresh_forecasts" else {}
        return fn(**kwargs), None
    except Exception as exc:
        logger.exception("Job %s failed: %s", job, exc)
        return None, str(exc)
