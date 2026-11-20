# residuecompass

Residue Compass helps paddy farmers decide whether to keep, sell, or use straw as animal feed, and coordinates collection logistics before wheat sowing.

---

## Part 4: Economics, Matching, and Validation

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-24%20passed-success.svg)](#running-tests)
[![Zero External Dependencies](https://img.shields.io/badge/dependencies-standard%20library-brightgreen.svg)](#installation--setup)

Part 4 provides the decision-making intelligence of **Residue Compass**. It calculates comparative on-farm economics (Keep vs. Sell vs. Feed), pairs village paddy straw supply with industrial buyers and agricultural logistics equipment (balers and trucks), quantifies diverted biomass and farmer revenues, and runs multi-scenario economic stress tests.

---

## 1. What Part 4 Does
1. **Comparative Economic Decisions:** Evaluates **KEEP**, **SELL**, and **FEED** on a strictly consistent net INR per metric tonne basis.
2. **Break-Even & Price Bands:** Computes the exact buyer offer price at which selling becomes superior to the best on-farm alternative, plus low/high recommended price ranges.
3. **What-If Sensitivity:** Dynamically recalculates recommendations and produces itemized diffs under fluctuating diesel prices, transport distances, baling rates, and fodder values.
4. **Spatio-Temporal Matching:** Greedily assigns villages to buyers, balers, and trucks under 12 hard operational constraints (capacities, active dates, sowing deadlines, and haversine road proxy distances).
5. **Impact Estimation:** Transparently accounts for contracted biomass diverted from burning, farmer net revenues, and avoided in-situ burning losses without false air quality claims.
6. **Stress Testing:** Audits policy and price robustness across fuel spikes, fertilizer subsidy shifts, market crashes, and long-haul distances.

## 2. What Part 4 Deliberately Does NOT Do
- **Does NOT** implement satellite image processing, NDVI, or active fire detection (owned by Part 2).
- **Does NOT** train or deploy harvest prediction or yield estimation ML models (owned by Part 3).
- **Does NOT** host persistent databases, user authentication, or primary REST servers (owned by Part 1).
- **Does NOT** implement user interfaces, mobile apps, or frontend web dashboards (owned by Part 5).
- **Does NOT** assert satellite-verified air pollution reduction without ground-truthed burn verification from Parts 1 & 3.

---

## 3. Project Structure

```text
RESIDUE-COMPASS/
├── src/
│   └── residue_compass_economics/
│       ├── __init__.py          # Public exports
│       ├── config.py            # Agronomic baselines & economic defaults
│       ├── schemas.py           # Validated data contracts (Pydantic-ready)
│       ├── exceptions.py        # Domain exceptions
│       ├── economics.py         # KEEP/SELL/FEED & break-even calculations
│       ├── matching.py          # 12-constraint spatio-temporal matching engine
│       ├── impact.py            # Biomass diversion and net revenue estimation
│       ├── validation.py        # Entity audits & multi-scenario stress tests
│       ├── service.py           # Stable public API for Part 1 import
│       ├── sample_data.py       # Realistic synthetic benchmark datasets
│       └── router.py            # Modular router adapter for FastAPI/Flask
├── tests/
│   ├── __init__.py
│   ├── test_economics.py        # Hand-calculated economics & what-if tests
│   ├── test_matching.py         # Capacity, date, and double-booking tests
│   ├── test_impact.py           # Diversion accounting & zero-division tests
│   ├── test_validation.py       # Schema & stress testing tests
│   └── test_integration.py      # End-to-end integration and API tests
├── examples/
│   ├── run_demo.py              # Single-command offline demonstration
│   ├── sample_forecasts.json    # Example forecast payload
│   ├── sample_decisions.json    # Example economic decision output
│   └── sample_matches.json      # Example dispatch booking output
├── docs/
│   ├── architecture.md          # Architecture & data flow diagrams
│   ├── integration_contract.md  # Exact JSON schemas, field names & units
│   ├── assumptions_and_limits.md# Research sources, proxy limits & warnings
│   └── algorithm_explanations.md# Detailed mathematical formulas & constraints
├── outputs/                     # Generated JSON outputs from demo runs
├── PROGRESS.md                  # Development trajectory and milestone log
├── HANDOFF.md                   # Team handoff report
├── pyproject.toml               # Package configuration
└── README.md
```

---

## 4. Installation & Setup

Part 4 requires **Python 3.11+** and uses **standard library components** for its core engine. Zero external packages are strictly required to run tests or the demo.

### Standard Setup
```bash
# Clone the repository and navigate into the project directory
cd "d:\IIT INDORE HACKATHON\RESIDUE-COMPASS"

# (Optional) Install in editable mode if running with full pip access:
pip install -e .
```

---

## 5. Running the Demo

Run the end-to-end offline demo with a single command:

```bash
python examples/run_demo.py
```

### What the demo executes:
1. Loads 4 synthetic villages, 3 buyers, 3 balers, and 4 trucks in Punjab/Haryana.
2. Validates contract integrity and capacity sanity.
3. Computes comparative economics across all villages:
   - **Profitable Sale:** Village `VIL-001` (Raikot Cluster) -> Recommends **SELL**.
   - **Local Fodder Superior:** Village `VIL-002` (Bhawanigarh Dairy Belt) -> Recommends **FEED**.
   - **Mulching Superior:** Village `VIL-003` (Samana Remote Farms) -> Recommends **KEEP**.
4. Recalculates decision under a diesel price spike and buyer price crash (**What-If**).
5. Runs the matching engine, creating 8 dispatch bookings and reporting remaining tonnes.
6. Computes contracted biomass diverted (310.0 tonnes) and farmer net income (INR 438,544.86).
7. Runs 6 robustness stress tests, highlighting recommendation flips and delta break-even.
8. Exports JSON files to the `outputs/` directory.

---

## 6. Running Tests

Run all unit and integration tests using Python's built-in test runner:

```bash
python -m unittest discover tests -v
```

All **24 tests** execute deterministically in **< 0.05 seconds**.

---

## 7. Economic Formulas

All comparisons are conducted on a consistent **INR per metric tonne** basis:

$$\text{Net Value}_{\text{option}} = \text{Gross Benefit}_{\text{option}} - \text{Incurred Costs}_{\text{option}}$$

### 1. KEEP (In-situ Mulching / Incorporation)
$$\text{Gross Keep} = \text{Nutrient Replacement Value} + \text{Soil Carbon/Moisture Benefit}$$
$$\text{Net Keep} = \text{Gross Keep} - \text{Super Seeder / Tractor Pass Cost}$$
*Default agronomic values per tonne of straw: 6 kg N (INR 36), 1.5 kg P2O5 (INR 44.25), 15 kg K2O (INR 510), 1.2 kg S (INR 18) + Soil Benefit (INR 350) - Incorporation (INR 520) = **INR 438.25/t net**.*

### 2. SELL (Ex-situ Off-farm Collection)
$$\text{Seller Costs} = \text{Baling Cost} + \text{Loading Cost} + (\text{Distance (km)} \times \text{Transport Rate})$$
$$\text{Net Sell} = \text{Offered Price} - \text{Seller Costs}$$
*(If buyer covers baling or transport, those terms drop to 0).*

### 3. FEED (Livestock Fodder)
$$\text{Feed Costs} = \text{Chopping / Urea Treatment Cost} + \text{Local Handling Cost}$$
$$\text{Net Feed} = \text{Local Fodder Market Price} - \text{Feed Costs}$$

### 4. Break-Even Selling Price
$$\text{Break-Even Price} = \max(\text{Net Keep}, \text{Net Feed}) + \text{Seller Costs}$$

---

## 8. Matching Algorithm & Operational Constraints

Part 4 implements a deterministic greedy priority matching engine. It optimizes resource allocation while strictly respecting 12 hard constraints:

1. **Supply Limit:** Village allocation $\le$ available straw forecast.
2. **Demand Limit:** Delivery $\le$ buyer remaining capacity.
3. **Baler Capacity:** Daily booking $\le$ baler daily rated capacity.
4. **Truck Capacity:** Daily booking $\le$ truck daily hauling capacity.
5. **Machine Availability:** Resource must be active and operational.
6. **Harvest Ready Date:** Pickup Date $\ge$ Harvest Date.
7. **Sowing Deadline:** Pickup Date $\le$ Collection Deadline (Wheat sowing cut-off).
8. **No Double-Booking:** Daily resource tonnage strictly capped per machine per date.
9. **Demand Validity:** Pickup Date $\le$ Buyer Offer Expiry Date.
10. **ID Integrity:** All referenced entities must be valid and present.
11. **Partial Match Handling:** Exact accounting of partially fulfilled lots.
12. **Determinism:** Fixed tie-breaking by entity ID ensures identical outputs on identical inputs.

---

## 9. Integration with Other Parts

### How Part 1 (Backend API) Imports Part 4
Part 1 directly imports the service functions or uses the provided router:

```python
from residue_compass_economics.service import (
    calculate_decision,
    run_what_if,
    run_matching,
    calculate_impact,
    run_stress_tests,
    validate_project_data,
)

# Example: Compute decision inside Part 1 endpoint
decision = calculate_decision(forecast_obj, economic_input_obj)
```

Part 1 can also mount `Part4APIRouter` into FastAPI or Flask. See `docs/integration_contract.md`.

### How Part 5 (Frontend) Consumes Outputs
Part 5 receives pure JSON payloads matching the schemas in `docs/integration_contract.md`:
- `best_choice`: string badge (`"keep" | "sell" | "feed"`).
- `break_even_price_inr_per_tonne`: currency stat display.
- `recommended_price_low_inr_per_tonne` & `recommended_price_high_inr_per_tonne`: recommended price band slider.
- `bookings`: list of dispatch cards displaying pickup dates, assigned machinery, and net revenue.
- `unmatched_villages`: alert cards with specific logistical bottleneck explanations.

---

## 10. Synthetic Data & Transparency Notice

All records provided in `sample_data.py` and example files are **synthetic benchmarks** carrying `is_simulated: true`. 
- Diversion estimates are reported as `estimated_tonnes_diverted` based on contracted collection bookings.
- Air pollution and emissions reductions cannot be claimed as verified without physical delivery weight receipts or Part 3 satellite fire verification.
