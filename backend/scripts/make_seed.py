import json
from pathlib import Path

SEED = Path(__file__).resolve().parents[1] / "seed"
SEED.mkdir(exist_ok=True)

villages = [
    {"village_id": "PB-SNG-0142", "village_name": "Sample Village", "district": "Sangrur",
     "centroid": {"type": "Point", "coordinates": [75.84, 30.25]}, "paddy_area_ha": 118.5,
     "harvest_status": "READY_SOON", "expected_harvest_date": "2026-10-20",
     "expected_straw_tonnes": 410.0, "confidence": "MEDIUM"},
    {"village_id": "PB-SNG-0187", "village_name": "Sample Village B", "district": "Sangrur",
     "centroid": {"type": "Point", "coordinates": [75.91, 30.31]}, "paddy_area_ha": 86.0,
     "harvest_status": "GROWING", "expected_harvest_date": "2026-10-27",
     "expected_straw_tonnes": 298.0, "confidence": "LOW"},
    {"village_id": "PB-TTN-0031", "village_name": "Sample Village C", "district": "Tarn Taran",
     "centroid": {"type": "Point", "coordinates": [74.93, 31.45]}, "paddy_area_ha": 142.3,
     "harvest_status": "HARVESTED", "expected_harvest_date": "2026-10-14",
     "expected_straw_tonnes": 492.0, "confidence": "HIGH"},
]

decisions = {
    "PB-SNG-0142": {
        "village_id": "PB-SNG-0142",
        "per_tonne_inr": {
            "keep": {"gain": 640, "cost": 450, "net": 190},
            "sell": {"gain": 1500, "cost": 1180, "net": 320},
            "feed": {"gain": 1100, "cost": 900, "net": 200},
        },
        "best_option": "sell",
        "break_even_price_per_tonne_inr": 1180,
        "price_range_inr": {"low": 1050, "high": 1320},
        "assumptions": {
            "fertilizer_value_per_tonne": 640,
            "baling_cost_per_tonne": 450,
            "transport_cost_per_tonne_per_km": 12,
            "distance_km": 38,
            "diesel_price_per_litre": 90,
        },
        "confidence": {"tag": "MEDIUM", "reasons": ["district-level prices used"]},
        "generated_at": "2026-10-12T06:05:00Z",
    }
}

matches = [
    {"match_id": "M-20261012-0007", "village_id": "PB-SNG-0142", "status": "PROPOSED",
     "tonnes": 410.0,
     "buyer": {"id": "B-012", "name": "Sample Pellet Unit", "type": "PELLET", "distance_km": 38},
     "baler": {"id": "BAL-031"}, "truck": {"id": "TRK-114"},
     "pickup_date": "2026-10-24", "price_per_tonne_inr": 1500, "net_to_farmers_inr": 131200,
     "saving_vs_burning_note": "Estimate, to be measured in the pilot",
     "created_at": "2026-10-12T06:10:00Z"},
    {"match_id": "M-20261012-0008", "village_id": "PB-TTN-0031", "status": "CONFIRMED",
     "tonnes": 492.0,
     "buyer": {"id": "B-004", "name": "Sample Biogas Plant", "type": "BIOGAS", "distance_km": 22},
     "baler": {"id": "BAL-012"}, "truck": {"id": "TRK-077"},
     "pickup_date": "2026-10-18", "price_per_tonne_inr": 1400, "net_to_farmers_inr": 118080,
     "saving_vs_burning_note": "Estimate, to be measured in the pilot",
     "created_at": "2026-10-12T06:10:00Z"},
]

burn_events = [
    {"event_id": "BE-20261023-0451", "village_id": "PB-SNG-0142",
     "location": {"type": "Point", "coordinates": [75.84, 30.25]},
     "detected_on": "2026-10-23", "confidence": "HIGH",
     "evidence": {"fire_points": 2, "burn_scar_detected": True, "burn_area_ha": 3.1},
     "source": "FIRMS+Sentinel-2"},
    {"event_id": "BE-20261024-0452", "village_id": "PB-SNG-0187",
     "location": {"type": "Point", "coordinates": [75.91, 30.31]},
     "detected_on": "2026-10-24", "confidence": "LOW",
     "evidence": {"fire_points": 1, "burn_scar_detected": False, "burn_area_ha": 0.0},
     "source": "FIRMS"},
]

for name, data in [("villages", villages), ("decisions", decisions),
                   ("matches", matches), ("burn_events", burn_events)]:
    (SEED / f"{name}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("written:", name)