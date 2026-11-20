# Algorithm Explanations: Economics & Matching

## 1. Economic Decision Engine

### 1.1. The Net Comparative Valuation Rule
Directly comparing a gross market offer with soil nutrient value is fundamentally flawed. Part 4 enforces **Net Comparable Value per Tonne (INR/tonne)**:

$$\text{Net Value}_{\text{option}} = \text{Gross Benefit}_{\text{option}} - \text{Direct Incurred Costs}_{\text{option}}$$

Where:
1. **KEEP:**
   $$\text{Net}_{\text{keep}} = (\text{Nutrient Value} + \text{Soil Physical Benefit}) - \text{Mulching / Machine Pass Cost}$$
2. **SELL:**
   $$\text{Net}_{\text{sell}} = \text{Offered Price} - (\text{Baling Cost} + \text{Loading Cost} + \text{Transport Cost})$$
   *(Note: Configurable cost-sharing allows buyers or aggregators to absorb baling or transport).*
3. **FEED:**
   $$\text{Net}_{\text{feed}} = \text{Local Fodder Value} - (\text{Chopping \& Treatment Cost} + \text{Local Handling})$$

### 1.2. Break-Even Price Formula
The minimum buyer offer price $P_{\text{break-even}}$ at which selling is economically equal or superior to the farmer's best alternative (keeping or feeding):

$$P_{\text{break-even}} = \max(\text{Net}_{\text{keep}}, \text{Net}_{\text{feed}}) + \text{Seller-Borne Collection Costs}$$

If a buyer offers less than $P_{\text{break-even}}$, the farmer is economically worse off selling than utilizing the straw on-farm.

### 1.3. Recommended Price Band
- **Low Target ($P_{\text{low}}$):** Break-even under favorable logistics (nearby drop-off, competitive baling rate).
- **High Target ($P_{\text{high}}$):** Fair value providing a 15–25% margin over the best non-sell alternative, compensating for scheduling friction and collection risk.

---

## 2. Spatio-Temporal Matching Engine

### 2.1. Objective Function
Maximize the net farmer value and total biomass diverted from burning within the tight agronomic window (typically 10 to 20 days between rice harvest and wheat sowing).

### 2.2. Greedy Priority Ranking
Potential village-buyer pairs are scored using:
$$\text{Score} = \text{Offered Price} - (\text{Transport Cost per km} \times \text{Distance}) - \text{Baler Cost} + \text{Urgency Weight}$$

Pairs with imminent harvest deadlines are prioritized to prevent farmers from burning out of panic.

### 2.3. Hard Constraints Enforced
1. **Supply Limit:** Village allocation $\le$ remaining uncommitted forecast straw.
2. **Demand Limit:** Delivery $\le$ buyer remaining capacity.
3. **Baler Capacity:** Assigned tonnes $\le$ baler daily rated capacity.
4. **Truck Capacity:** Assigned tonnes $\le$ truck daily hauling capacity.
5. **Machine Availability:** Resource must be active and operational on the scheduled date.
6. **Harvest Ready Date:** Pickup Date $\ge$ Harvest Date.
7. **Sowing Deadline:** Pickup Date $\le$ Collection Deadline (Wheat sowing cut-off).
8. **No Double-Booking:** Single booking per machine/truck per day (or daily tonnage cap strictly enforced).
9. **Demand Validity:** Pickup Date $\le$ Buyer Offer Expiry Date.
10. **ID Integrity:** All referenced entities must be valid and present.
11. **Partial Match Handling:** Exact accounting of partially fulfilled lots.
12. **Determinism:** Fixed tie-breaking by entity ID and economic margin ensures identical outputs on identical inputs.
