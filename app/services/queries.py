from sqlalchemy import text

from app.core.db import engine


def _village_row_to_dict(r):
    return {
        "village_id": r["village_id"],
        "village_name": r["village_name"],
        "district": r["district"],
        "centroid": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
        "paddy_area_ha": r["paddy_area_ha"],
        "harvest_status": r["harvest_status"],
        "expected_harvest_date": r["harvest_expected"],
        "expected_straw_tonnes": r["straw_expected"],
        "confidence": r["confidence_tag"],
    }


def list_villages(district=None):
    sql = text("""
        SELECT DISTINCT ON (v.id)
               v.id AS village_id, v.name AS village_name, d.name AS district,
               ST_X(v.centroid) AS lon, ST_Y(v.centroid) AS lat,
               v.paddy_area_ha, f.harvest_status, f.harvest_expected,
               f.straw_expected, f.confidence_tag
        FROM villages v
        JOIN districts d ON d.id = v.district_id
        JOIN forecasts f ON f.village_id = v.id
        WHERE (CAST(:district AS text) IS NULL OR lower(d.name) = lower(CAST(:district AS text)))
        ORDER BY v.id, f.generated_at DESC, f.id DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"district": district}).mappings().all()
    return [_village_row_to_dict(r) for r in rows]


def get_village(village_id):
    for v in list_villages():
        if v["village_id"] == village_id:
            return v
    return None


def get_forecast(village_id):
    sql = text("""
        SELECT f.*, v.name AS village_name, d.name AS district
        FROM forecasts f
        JOIN villages v ON v.id = f.village_id
        JOIN districts d ON d.id = v.district_id
        WHERE f.village_id = :vid
        ORDER BY f.generated_at DESC, f.id DESC
        LIMIT 1
    """)
    with engine.connect() as conn:
        r = conn.execute(sql, {"vid": village_id}).mappings().first()
    if r is None:
        return None
    return {
        "village_id": r["village_id"],
        "village_name": r["village_name"],
        "district": r["district"],
        "season": r["season"],
        "harvest": {
            "expected_date": r["harvest_expected"],
            "earliest_date": r["harvest_earliest"],
            "latest_date": r["harvest_latest"],
        },
        "straw": {
            "paddy_area_ha": r["paddy_area_ha"],
            "expected_tonnes": r["straw_expected"],
            "low_tonnes": r["straw_low"],
            "high_tonnes": r["straw_high"],
        },
        "confidence": {"tag": r["confidence_tag"], "reasons": r["reasons"]},
        "model_version": r["model_version"],
        "generated_at": r["generated_at"],
    }


def get_decision(village_id):
    sql = text("""
        SELECT * FROM decisions
        WHERE village_id = :vid
        ORDER BY generated_at DESC, id DESC
        LIMIT 1
    """)
    with engine.connect() as conn:
        r = conn.execute(sql, {"vid": village_id}).mappings().first()
    if r is None:
        return None
    return {
        "village_id": r["village_id"],
        "per_tonne_inr": r["per_tonne"],
        "best_option": r["best_option"],
        "break_even_price_per_tonne_inr": r["break_even_price"],
        "price_range_inr": {"low": r["price_low"], "high": r["price_high"]},
        "assumptions": r["assumptions"],
        "confidence": {"tag": r["confidence_tag"], "reasons": r["confidence_reasons"]},
        "generated_at": r["generated_at"],
    }


def list_matches(status=None, village_id=None):
    sql = text("""
        SELECT m.match_id, m.village_id, m.status, m.tonnes, m.pickup_date,
               m.price_per_tonne_inr, m.net_to_farmers_inr, m.created_at,
               m.baler_id, m.truck_id,
               b.id AS buyer_id, b.name AS buyer_name, b.type AS buyer_type,
               round((ST_Distance(b.geom::geography, v.centroid::geography) / 1000)::numeric, 1)
                 AS distance_km
        FROM matches m
        JOIN buyers b ON b.id = m.buyer_id
        JOIN villages v ON v.id = m.village_id
        WHERE (CAST(:status AS text) IS NULL OR m.status = CAST(:status AS text))
          AND (CAST(:vid AS text) IS NULL OR m.village_id = CAST(:vid AS text))
        ORDER BY m.created_at DESC, m.match_id
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"status": status, "vid": village_id}).mappings().all()
    return [
        {
            "match_id": r["match_id"],
            "village_id": r["village_id"],
            "status": r["status"],
            "tonnes": r["tonnes"],
            "buyer": {
                "id": r["buyer_id"], "name": r["buyer_name"],
                "type": r["buyer_type"], "distance_km": r["distance_km"],
            },
            "baler": {"id": r["baler_id"]},
            "truck": {"id": r["truck_id"]},
            "pickup_date": r["pickup_date"],
            "price_per_tonne_inr": r["price_per_tonne_inr"],
            "net_to_farmers_inr": r["net_to_farmers_inr"],
            "saving_vs_burning_note": "Estimate, to be measured in the pilot",
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def list_burn_events(village_id=None, confidence=None):
    sql = text("""
        SELECT event_id, village_id, ST_X(geom) AS lon, ST_Y(geom) AS lat,
               detected_on, confidence_tag, evidence, source
        FROM burn_events
        WHERE (CAST(:vid AS text) IS NULL OR village_id = CAST(:vid AS text))
          AND (CAST(:conf AS text) IS NULL OR confidence_tag = CAST(:conf AS text))
        ORDER BY detected_on DESC, event_id
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"vid": village_id, "conf": confidence}).mappings().all()
    return [
        {
            "event_id": r["event_id"],
            "village_id": r["village_id"],
            "location": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            "detected_on": r["detected_on"],
            "confidence": r["confidence_tag"],
            "evidence": r["evidence"],
            "source": r["source"],
        }
        for r in rows
    ]