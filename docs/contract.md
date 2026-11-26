# Residue Compass: API and Data Contract (v1)

Owner: Part 1 (Backend and Integration).
Rule: **never rename or remove a field without telling everyone.** Adding a new field is fine.

Base URL (local): `http://127.0.0.1:8000/api/v1`
Live docs: `/docs` on the same server.

## 1. Conventions

| Item | Rule |
|---|---|
| Village ID | Text like `PB-SNG-0142` (state-district-number). Part 2 owns the master list. |
| Dates | `YYYY-MM-DD` (example `2026-10-20`) |
| Timestamps | UTC, ISO 8601 with Z (example `2026-10-12T06:00:00Z`) |
| Geometry | GeoJSON, coordinates are `[longitude, latitude]` |
| Units | tonnes, hectares, kilometres, rupees (INR). Unit is part of the field name. |
| Confidence | Exactly one of `LOW`, `MEDIUM`, `HIGH` |
| Match status | `PROPOSED`, `CONFIRMED`, `COMPLETED`, `CANCELLED` |
| Harvest status | `GROWING`, `READY_SOON`, `HARVESTED` |
| Decision options | `keep`, `sell`, `feed` |
| Buyer types | `POWER`, `PELLET`, `BIOGAS`, `OTHER` |

## 2. Error format (all errors)

```json
{ "detail": { "error": { "code": "VILLAGE_NOT_FOUND", "message": "No village with this ID.", "field": "village_id" } } }
```

## 3. Endpoints

### Available now (mock data)

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | `{"status":"ok","demo_mode":true}` |
| GET | `/villages?district=` | list of village summaries |
| GET | `/villages/{village_id}` | one village summary |
| GET | `/villages/{village_id}/forecast` | forecast object |
| GET | `/villages/{village_id}/decision` | decision object |
| GET | `/matches?status=&village_id=` | list of matches |
| GET | `/burn-events?village_id=&confidence=` | list of burn events |

### Planned (we will add these)

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | get a token (roles: officer, farmer, buyer) |
| POST | `/decisions/simulate` | what-if with edited assumptions |
| POST | `/matches/{id}/confirm` | farmer or buyer confirms pickup |
| GET | `/buyers` | buyer registry and demand |
| GET | `/notifications` | log of messages sent |
| POST | `/jobs/run` and GET `/jobs/{run_id}` | run the pipeline, check progress |
| POST | `/demo/run` | one-click full loop |

## 4. Sample objects

The exact samples live in `backend/seed/*.json`. These files are the source of truth for shapes:

- `villages.json` (village summary)
- `forecasts.json` (forecast)
- `decisions.json` (decision)
- `matches.json` (match)
- `burn_events.json` (burn event)

The Python versions of the shapes are in `backend/app/schemas/`.

All numbers in seed files are **illustrative sample data**, not real results.

## 5. What each teammate hands over

### Part 2: Satellite and map data
Deliver files in `data_pipeline/output/` with these exact columns:

- `villages.geojson`: `village_id`, `village_name`, `district`, `paddy_area_ha`, geometry (polygon)
- `ndvi_observations.csv`: `village_id`, `obs_date`, `ndvi_mean`, `ndvi_median`, `cloud_pct`, `quality_flag`
- `weather_observations.csv`: `village_id`, `obs_date`, `rain_mm`, `temp_max_c`, `temp_min_c`, `source`
- `fire_detections.csv`: `acq_datetime`, `latitude`, `longitude`, `brightness`, `frp`, `sat_confidence`, `village_id`
- `burn_scars.csv`: `village_id`, `detected_on`, `area_ha`

### Part 3: ML
Provide in `ml/predict.py`:

```python
def predict_village(village_id: str) -> dict:
    """Return a dict with exactly the forecast shape in seed/forecasts.json"""

def verify_village(village_id: str) -> list[dict]:
    """Return a list of burn events, each in the shape of seed/burn_events.json"""
```

### Part 4: Economics and matching
Provide in `economics/decide.py` and `economics/match.py`:

```python
def decide(village_id: str, assumptions: dict | None = None) -> dict:
    """Return exactly the decision shape in seed/decisions.json"""

def run_matching() -> list[dict]:
    """Return a list of matches in the shape of seed/matches.json"""
```

### Part 5: Frontend
Call the endpoints above. Keep the API base URL in one config setting. Build screens against the seed shapes. Handle loading, empty and error states.

## 6. Change rules

1. Contract changes go through a pull request that edits this file.
2. Adding a field: announce it in the group chat.
3. Renaming or removing a field: needs agreement from everyone, and a new version (`/api/v2`) if it breaks anyone.
4. Every prediction carries a `confidence` tag and, where possible, `reasons`.
5. Every number that is a guess is labeled as an assumption or estimate.