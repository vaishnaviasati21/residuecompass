import json
from datetime import date, datetime, timedelta

from sqlalchemy import text

from app.adapters.seed_loader import load_seed
from app.core.config import settings
from app.core.db import engine


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main():
    if not settings.DEMO_MODE:
        raise RuntimeError(
            "Refusing to run load_seed.py when DEMO_MODE=false because it truncates operational tables."
        )
    villages = load_seed("villages")
    forecasts = load_seed("forecasts")
    decisions = load_seed("decisions")
    matches = load_seed("matches")
    burns = load_seed("burn_events")

    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE forecasts, decisions, matches, burn_events RESTART IDENTITY CASCADE"
        ))

        # Forecasts: use the detailed seed if present, otherwise build one from the village summary
        for v in villages:
            f = forecasts.get(v["village_id"])
            if f is None:
                d = date.fromisoformat(v["expected_harvest_date"])
                s = v["expected_straw_tonnes"]
                f = {
                    "season": "kharif-2026",
                    "harvest": {
                        "expected_date": v["expected_harvest_date"],
                        "earliest_date": (d - timedelta(days=4)).isoformat(),
                        "latest_date": (d + timedelta(days=5)).isoformat(),
                    },
                    "straw": {
                        "paddy_area_ha": v["paddy_area_ha"],
                        "expected_tonnes": s,
                        "low_tonnes": round(s * 0.88, 1),
                        "high_tonnes": round(s * 1.11, 1),
                    },
                    "confidence": {"tag": v["confidence"], "reasons": ["sample data"]},
                    "model_version": "mock-0.1",
                    "generated_at": "2026-10-12T06:00:00Z",
                }
            conn.execute(text("""
                INSERT INTO forecasts
                (village_id, season, harvest_expected, harvest_earliest, harvest_latest,
                 paddy_area_ha, straw_expected, straw_low, straw_high, confidence_tag,
                 reasons, model_version, generated_at, harvest_status)
                VALUES
                (:vid, :season, :he, :hea, :hl, :area, :se, :sl, :sh, :tag,
                 CAST(:reasons AS jsonb), :mv, :gen, :hs)
            """), {
                "vid": v["village_id"], "season": f["season"],
                "he": date.fromisoformat(f["harvest"]["expected_date"]),
                "hea": date.fromisoformat(f["harvest"]["earliest_date"]),
                "hl": date.fromisoformat(f["harvest"]["latest_date"]),
                "area": f["straw"]["paddy_area_ha"],
                "se": f["straw"]["expected_tonnes"],
                "sl": f["straw"]["low_tonnes"],
                "sh": f["straw"]["high_tonnes"],
                "tag": f["confidence"]["tag"],
                "reasons": json.dumps(f["confidence"]["reasons"]),
                "mv": f["model_version"], "gen": ts(f["generated_at"]),
                "hs": v["harvest_status"],
            })

        for vid, d in decisions.items():
            conn.execute(text("""
                INSERT INTO decisions
                (village_id, per_tonne, best_option, break_even_price, price_low, price_high,
                 assumptions, confidence_tag, confidence_reasons, generated_at)
                VALUES
                (:vid, CAST(:pt AS jsonb), :best, :be, :pl, :ph,
                 CAST(:ass AS jsonb), :tag, CAST(:reasons AS jsonb), :gen)
            """), {
                "vid": vid, "pt": json.dumps(d["per_tonne_inr"]),
                "best": d["best_option"], "be": d["break_even_price_per_tonne_inr"],
                "pl": d["price_range_inr"]["low"], "ph": d["price_range_inr"]["high"],
                "ass": json.dumps(d["assumptions"]),
                "tag": d["confidence"]["tag"],
                "reasons": json.dumps(d["confidence"]["reasons"]),
                "gen": ts(d["generated_at"]),
            })

        for m in matches:
            conn.execute(text("""
                INSERT INTO matches
                (match_id, village_id, buyer_id, baler_id, truck_id, tonnes, pickup_date,
                 price_per_tonne_inr, status, created_at, net_to_farmers_inr)
                VALUES
                (:id, :vid, :bid, :bal, :trk, :t, :pd, :price, :st, :ca, :net)
            """), {
                "id": m["match_id"], "vid": m["village_id"], "bid": m["buyer"]["id"],
                "bal": m["baler"]["id"], "trk": m["truck"]["id"], "t": m["tonnes"],
                "pd": date.fromisoformat(m["pickup_date"]),
                "price": m["price_per_tonne_inr"], "st": m["status"],
                "ca": ts(m["created_at"]), "net": m["net_to_farmers_inr"],
            })

        for b in burns:
            lon, lat = b["location"]["coordinates"]
            conn.execute(text("""
                INSERT INTO burn_events
                (event_id, village_id, geom, detected_on, confidence_tag, evidence, source)
                VALUES
                (:id, :vid, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :dt, :tag,
                 CAST(:ev AS jsonb), :src)
            """), {
                "id": b["event_id"], "vid": b["village_id"], "lon": lon, "lat": lat,
                "dt": date.fromisoformat(b["detected_on"]), "tag": b["confidence"],
                "ev": json.dumps(b["evidence"]), "src": b["source"],
            })

    print("Seed data loaded into the database.")


if __name__ == "__main__":
    main()