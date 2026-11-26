CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS districts (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  state TEXT NOT NULL,
  geom geometry(MultiPolygon, 4326)
);

CREATE TABLE IF NOT EXISTS villages (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  district_id INT REFERENCES districts(id),
  geom geometry(MultiPolygon, 4326) NOT NULL,
  centroid geometry(Point, 4326),
  paddy_area_ha NUMERIC
);
CREATE INDEX IF NOT EXISTS idx_villages_geom ON villages USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_villages_centroid ON villages USING GIST (centroid);

CREATE TABLE IF NOT EXISTS ndvi_observations (
  id BIGSERIAL PRIMARY KEY,
  village_id TEXT NOT NULL REFERENCES villages(id),
  obs_date DATE NOT NULL,
  ndvi_mean NUMERIC,
  ndvi_median NUMERIC,
  cloud_pct NUMERIC,
  quality_flag TEXT,
  UNIQUE (village_id, obs_date)
);

CREATE TABLE IF NOT EXISTS weather_observations (
  id BIGSERIAL PRIMARY KEY,
  village_id TEXT NOT NULL REFERENCES villages(id),
  obs_date DATE NOT NULL,
  rain_mm NUMERIC,
  temp_max_c NUMERIC,
  temp_min_c NUMERIC,
  source TEXT,
  UNIQUE (village_id, obs_date)
);

CREATE TABLE IF NOT EXISTS fire_detections (
  id BIGSERIAL PRIMARY KEY,
  geom geometry(Point, 4326) NOT NULL,
  acq_datetime TIMESTAMPTZ NOT NULL,
  brightness NUMERIC,
  frp NUMERIC,
  sat_confidence TEXT,
  village_id TEXT REFERENCES villages(id)
);
CREATE INDEX IF NOT EXISTS idx_fire_geom ON fire_detections USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_fire_time ON fire_detections (acq_datetime);

CREATE TABLE IF NOT EXISTS burn_scars (
  id BIGSERIAL PRIMARY KEY,
  village_id TEXT NOT NULL REFERENCES villages(id),
  detected_on DATE NOT NULL,
  area_ha NUMERIC,
  geom geometry(MultiPolygon, 4326)
);

CREATE TABLE IF NOT EXISTS forecasts (
  id BIGSERIAL PRIMARY KEY,
  village_id TEXT NOT NULL REFERENCES villages(id),
  season TEXT NOT NULL,
  harvest_expected DATE NOT NULL,
  harvest_earliest DATE,
  harvest_latest DATE,
  paddy_area_ha NUMERIC,
  straw_expected NUMERIC NOT NULL,
  straw_low NUMERIC,
  straw_high NUMERIC,
  confidence_tag TEXT NOT NULL CHECK (confidence_tag IN ('LOW','MEDIUM','HIGH')),
  reasons JSONB DEFAULT '[]'::jsonb,
  model_version TEXT,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_forecasts_village ON forecasts (village_id, generated_at DESC);

CREATE TABLE IF NOT EXISTS decisions (
  id BIGSERIAL PRIMARY KEY,
  village_id TEXT NOT NULL REFERENCES villages(id),
  forecast_id BIGINT REFERENCES forecasts(id),
  per_tonne JSONB NOT NULL,
  best_option TEXT NOT NULL CHECK (best_option IN ('keep','sell','feed')),
  break_even_price NUMERIC NOT NULL,
  price_low NUMERIC,
  price_high NUMERIC,
  assumptions JSONB NOT NULL,
  confidence_tag TEXT CHECK (confidence_tag IN ('LOW','MEDIUM','HIGH')),
  confidence_reasons JSONB DEFAULT '[]'::jsonb,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_decisions_village ON decisions (village_id, generated_at DESC);

CREATE TABLE IF NOT EXISTS burn_events (
  event_id TEXT PRIMARY KEY,
  village_id TEXT NOT NULL REFERENCES villages(id),
  geom geometry(Point, 4326) NOT NULL,
  detected_on DATE NOT NULL,
  confidence_tag TEXT NOT NULL CHECK (confidence_tag IN ('LOW','MEDIUM','HIGH')),
  evidence JSONB,
  source TEXT
);
CREATE INDEX IF NOT EXISTS idx_burn_geom ON burn_events USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_burn_date ON burn_events (detected_on);

CREATE TABLE IF NOT EXISTS buyers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('POWER','PELLET','BIOGAS','OTHER')),
  geom geometry(Point, 4326) NOT NULL,
  capacity_t_per_day NUMERIC,
  price_per_tonne_inr NUMERIC,
  active BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_buyers_geom ON buyers USING GIST (geom);

CREATE TABLE IF NOT EXISTS machines (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL DEFAULT 'baler',
  base_geom geometry(Point, 4326),
  capacity_t_per_day NUMERIC,
  rate_per_tonne_inr NUMERIC,
  available_from DATE
);

CREATE TABLE IF NOT EXISTS trucks (
  id TEXT PRIMARY KEY,
  base_geom geometry(Point, 4326),
  capacity_t NUMERIC,
  rate_per_km_inr NUMERIC,
  available_from DATE
);

CREATE TABLE IF NOT EXISTS matches (
  match_id TEXT PRIMARY KEY,
  village_id TEXT NOT NULL REFERENCES villages(id),
  buyer_id TEXT NOT NULL REFERENCES buyers(id),
  baler_id TEXT REFERENCES machines(id),
  truck_id TEXT REFERENCES trucks(id),
  tonnes NUMERIC NOT NULL,
  pickup_date DATE NOT NULL,
  price_per_tonne_inr NUMERIC NOT NULL,
  status TEXT NOT NULL DEFAULT 'PROPOSED'
    CHECK (status IN ('PROPOSED','CONFIRMED','COMPLETED','CANCELLED')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_matches_village ON matches (village_id);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches (status);

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  phone TEXT UNIQUE,
  email TEXT UNIQUE,
  password_hash TEXT,
  role TEXT NOT NULL CHECK (role IN ('officer','farmer','buyer')),
  village_id TEXT REFERENCES villages(id),
  buyer_id TEXT REFERENCES buyers(id),
  language TEXT NOT NULL DEFAULT 'en' CHECK (language IN ('en','hi','pa'))
);

CREATE TABLE IF NOT EXISTS notifications (
  id BIGSERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  match_id TEXT REFERENCES matches(match_id),
  channel TEXT NOT NULL DEFAULT 'log',
  language TEXT NOT NULL DEFAULT 'en',
  body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  provider_id TEXT,
  sent_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGSERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  action TEXT NOT NULL,
  entity TEXT,
  entity_id TEXT,
  details JSONB,
  at TIMESTAMPTZ NOT NULL DEFAULT now()
);