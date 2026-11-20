# Integration Contract: Part 4 Engine

## 1. Overview
This document specifies the exact JSON schemas, units, enums, and signatures exposed by Part 4 (`residue_compass_economics`) to Part 1 (Backend API) and Part 5 (Frontend).

## 2. Standard Units and Conventions
- **Currency:** Indian Rupee (`INR`)
- **Mass:** Metric tonnes (`tonne`, `1 tonne = 1000 kg`)
- **Distance:** Kilometres (`km`)
- **Dates:** ISO 8601 strings (`YYYY-MM-DD`)
- **Confidence Levels:** Enum `["Low", "Medium", "High"]`
- **Decision Outcomes:** Enum `["keep", "sell", "feed"]`
- **Naming Convention:** `snake_case` across all JSON keys and Python attributes.

## 3. Public Service Interface (`service.py`)
Part 1 can import the following entry-point functions:

```python
from residue_compass_economics.service import (
    calculate_decision,
    run_what_if,
    run_matching,
    calculate_impact,
    run_stress_tests,
    validate_project_data,
)
```

### 3.1. Calculate Decision
- **Signature:** `calculate_decision(forecast: VillageStrawForecast, economic_input: Optional[VillageEconomicInput] = None, assumptions: Optional[EconomicsConfig] = None) -> EconomicDecision`
- **Description:** Evaluates net comparative values for KEEP, SELL, and FEED options, calculates break-even price and recommended price band.

### 3.2. Run What-If Analysis
- **Signature:** `run_what_if(base_forecast: VillageStrawForecast, base_input: VillageEconomicInput, overrides: Dict[str, Any], assumptions: Optional[EconomicsConfig] = None) -> WhatIfResult`
- **Description:** Applies overrides to assumptions or market parameters and outputs the updated decision alongside an itemized diff.

### 3.3. Run Matching
- **Signature:** `run_matching(forecasts: List[VillageStrawForecast], buyers: List[Buyer], balers: List[Baler], trucks: List[Truck], config: Optional[MatchingConfig] = None) -> MatchingResult`
- **Description:** Produces feasible bookings respecting all 12 operational constraints, and reports unmatched supply, unfilled demand, and unscheduled resources.

### 3.4. Calculate Impact
- **Signature:** `calculate_impact(forecasts: List[VillageStrawForecast], bookings: List[MatchBooking], assumptions: Optional[EconomicsConfig] = None) -> ImpactSummary`
- **Description:** Computes biomass diverted from open burning, total net revenue generated, and savings vs. burning.

### 3.5. Run Stress Tests
- **Signature:** `run_stress_tests(base_forecast: VillageStrawForecast, base_input: VillageEconomicInput, scenarios: Optional[List[StressScenario]] = None, assumptions: Optional[EconomicsConfig] = None) -> StressTestReport`
- **Description:** Tests the sensitivity of economic decisions across fuel spikes, transport shifts, fodder crashes, and price swings.

### 3.6. Validate Project Data
- **Signature:** `validate_project_data(forecasts: List[VillageStrawForecast], buyers: List[Buyer], balers: List[Baler], trucks: List[Truck]) -> ValidationResult`
- **Description:** Performs full schema, date sanity, coordinate boundary, and capacity checks before initiating matching.
