# Assumptions, Baselines, and Operational Limits

## 1. Agronomic & Economic Baselines
All default parameters are based on established Indian agricultural research (ICAR, PAU, and state agricultural extension guidelines) and are fully configurable.

### 1.1. Paddy Straw Nutrient Content (per metric tonne of dry straw)
- **Nitrogen (N):** ~6.0 kg/tonne (Urea equivalent)
- **Phosphorus (P2O5):** ~1.5 kg/tonne (DAP equivalent)
- **Potassium (K2O):** ~15.0 kg/tonne (MOP equivalent)
- **Sulfur (S):** ~1.2 kg/tonne
- **Organic Carbon:** ~400 kg organic carbon/tonne
- **Soil Structure & Moisture Benefit:** Valued conservatively as equivalent to reduced irrigation pass and weed suppression.

### 1.2. Operational Costs (North-Western Indian Plains baseline)
- **Super Seeder / Mulcher In-situ Management (KEEP):**
  - Machine rent & tractor diesel: ~INR 1,200 - 1,800 per acre (~INR 400 - 600 per tonne of straw).
- **Ex-situ Baling & Loading (SELL):**
  - Round/square baler service: ~INR 600 - 850 per tonne.
  - Manual loading into trolleys/trucks: ~INR 150 - 250 per tonne.
  - Transport: Fixed base flag fall (~INR 200/tonne) + ~INR 4.50 - 7.00 per tonne-km (depending on diesel price).
- **Animal Feed (FEED):**
  - Fodder replacement value: ~INR 1,500 - 2,500 per tonne.
  - Chopping, urea/molasses treatment for palatability: ~INR 400 - 600 per tonne.

## 2. Synthetic Data Transparency
- All sample records generated in `sample_data.py` are strictly synthetic benchmarks.
- Each record carries `is_simulated: true` or clear metadata flags.
- Real deployments must connect to local APMC mandi price feeds and district cooperative registries.

## 3. Scope Boundaries & Limitations
- **Road Distance Proxy:** When real routing network distances (OSRM/Google Maps) are unavailable, Part 4 computes Haversine great-circle distance with a documented regional winding factor (default 1.28x). This is clearly flagged in outputs.
- **Air Quality Claims:** Diverted biomass is calculated strictly as `estimated_tonnes_diverted`. Residue Compass Part 4 does *not* claim satellite-verified particulate emission reductions without ground-truthed burning verification (Part 3).
