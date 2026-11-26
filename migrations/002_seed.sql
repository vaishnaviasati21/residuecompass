INSERT INTO districts (name, state) VALUES
  ('Sangrur', 'Punjab'),
  ('Tarn Taran', 'Punjab')
ON CONFLICT (name) DO NOTHING;

INSERT INTO villages (id, name, district_id, geom, centroid, paddy_area_ha) VALUES
('PB-SNG-0142', 'Sample Village',
  (SELECT id FROM districts WHERE name='Sangrur'),
  ST_Multi(ST_GeomFromText('POLYGON((75.83 30.24, 75.85 30.24, 75.85 30.26, 75.83 30.26, 75.83 30.24))', 4326)),
  ST_SetSRID(ST_MakePoint(75.84, 30.25), 4326), 118.5),
('PB-SNG-0187', 'Sample Village B',
  (SELECT id FROM districts WHERE name='Sangrur'),
  ST_Multi(ST_GeomFromText('POLYGON((75.90 30.30, 75.92 30.30, 75.92 30.32, 75.90 30.32, 75.90 30.30))', 4326)),
  ST_SetSRID(ST_MakePoint(75.91, 30.31), 4326), 86.0),
('PB-TTN-0031', 'Sample Village C',
  (SELECT id FROM districts WHERE name='Tarn Taran'),
  ST_Multi(ST_GeomFromText('POLYGON((74.92 31.44, 74.94 31.44, 74.94 31.46, 74.92 31.46, 74.92 31.44))', 4326)),
  ST_SetSRID(ST_MakePoint(74.93, 31.45), 4326), 142.3)
ON CONFLICT (id) DO NOTHING;

INSERT INTO buyers (id, name, type, geom, capacity_t_per_day, price_per_tonne_inr) VALUES
('B-012', 'Sample Pellet Unit', 'PELLET', ST_SetSRID(ST_MakePoint(75.60, 30.40), 4326), 150, 1500),
('B-004', 'Sample Biogas Plant', 'BIOGAS', ST_SetSRID(ST_MakePoint(74.80, 31.30), 4326), 120, 1400)
ON CONFLICT (id) DO NOTHING;

INSERT INTO machines (id, kind, base_geom, capacity_t_per_day, rate_per_tonne_inr, available_from) VALUES
('BAL-031', 'baler', ST_SetSRID(ST_MakePoint(75.80, 30.22), 4326), 60, 450, '2026-10-15'),
('BAL-012', 'baler', ST_SetSRID(ST_MakePoint(74.90, 31.40), 4326), 55, 450, '2026-10-12')
ON CONFLICT (id) DO NOTHING;

INSERT INTO trucks (id, base_geom, capacity_t, rate_per_km_inr, available_from) VALUES
('TRK-114', ST_SetSRID(ST_MakePoint(75.82, 30.20), 4326), 12, 12, '2026-10-15'),
('TRK-077', ST_SetSRID(ST_MakePoint(74.91, 31.41), 4326), 12, 12, '2026-10-12')
ON CONFLICT (id) DO NOTHING;