# Residue Compass – PostGIS Database Schema

Engine: **PostgreSQL 16 + PostGIS 3.4** (`EPSG:4326`, WGS 84).  
Migrations live in [`backend/migrations/`](../backend/migrations/) (`001_init.sql`–`005b_seed_demo_users.py`), with SQLAlchemy + GeoAlchemy2 ORM mirrors in [`backend/app/models/tables.py`](../backend/app/models/tables.py).

## Entity Relationship Overview

```
districts ──< villages ──< ndvi_observations
                    │  ──< weather_observations
                    │  ──< fire_detections
                    │  ──< burn_scars
                    │  ──< forecasts ──< decisions
                    │  ──< burn_events
                    │  ──< matches >── buyers
                    │          │   >── machines (balers)
                    │          │   >── trucks
                    │          └──< notifications >── users
```

## Main Tables & Spatial Indexes

| Table | Purpose | Geometry / Key Columns | Indexes |
|---|---|---|---|
| `districts` | District boundaries & state metadata | `geom` (`MultiPolygon, 4326`) | `name` unique |
| `villages` | Master village list (`PB-SNG-0142`, etc.) | `geom` (`MultiPolygon`), `centroid` (`Point`), `paddy_area_ha` | `GIST(geom)`, `GIST(centroid)` |
| `ndvi_observations` | Sentinel-2 NDVI time series per village | `village_id`, `obs_date`, `ndvi_mean`, `cloud_pct` | Unique `(village_id, obs_date)` |
| `weather_observations` | ERA5 / IMD weather per village | `village_id`, `obs_date`, `rain_mm`, `temp_max_c`, `temp_min_c` | Unique `(village_id, obs_date)` |
| `fire_detections` | NASA FIRMS active fire points | `geom` (`Point, 4326`), `acq_datetime`, `brightness`, `frp` | `GIST(geom)`, `(acq_datetime)` |
| `burn_scars` | Post-fire Sentinel-2 burn scars | `village_id`, `detected_on`, `area_ha`, `geom` (`MultiPolygon`) | — |
| `forecasts` | Harvest date + straw tonnage + confidence | `harvest_expected`, `straw_expected`, `confidence_tag`, `harvest_status` | `(village_id, generated_at DESC)` |
| `decisions` | Keep vs. sell vs. feed economics + break-even | `per_tonne` (`JSONB`), `best_option`, `break_even_price`, `assumptions` (`JSONB`) | `(village_id, generated_at DESC)` |
| `burn_events` | Verified burn events with confidence tag | `geom` (`Point, 4326`), `detected_on`, `confidence_tag`, `evidence` (`JSONB`) | `GIST(geom)`, `(detected_on)` |
| `buyers` | Power, pellet, and biogas plants | `geom` (`Point, 4326`), `type`, `capacity_t_per_day`, `price_per_tonne_inr` | `GIST(geom)` |
| `machines` | Balers with base location & daily capacity | `base_geom` (`Point, 4326`), `rate_per_tonne_inr`, `available_from` | — |
| `trucks` | Haulage trucks with capacity & per-km rate | `base_geom` (`Point, 4326`), `capacity_t`, `rate_per_km_inr` | — |
| `matches` | Village–buyer–baler–truck pickup schedule | `status`, `tonnes`, `pickup_date`, `price_per_tonne_inr`, `net_to_farmers_inr` | `(village_id)`, `(status)` |
| `users` | Role-based accounts (`officer`, `farmer`, `buyer`) | `phone`, `email`, `role`, `village_id`, `buyer_id`, `language` (`en`/`hi`/`pa`) | `(phone)`, `(email)`, `(role)` |
| `notifications` | SMS / WhatsApp / log audit trail | `user_id`, `match_id`, `channel`, `language`, `body`, `status` | `(sent_at DESC)`, `(match_id)` |
| `audit_log` | Action trail for governance & debugging | `user_id`, `action`, `entity`, `entity_id`, `details` (`JSONB`) | `(entity, entity_id)` |
