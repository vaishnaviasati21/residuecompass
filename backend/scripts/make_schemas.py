from pathlib import Path

SCHEMAS = Path(__file__).resolve().parents[1] / "app" / "schemas"
SCHEMAS.mkdir(parents=True, exist_ok=True)

files = {}

files["common.py"] = '''from typing import List, Literal
from pydantic import BaseModel

ConfidenceTag = Literal["LOW", "MEDIUM", "HIGH"]


class Point(BaseModel):
    type: Literal["Point"]
    coordinates: List[float]
'''

files["village.py"] = '''from datetime import date
from typing import Literal
from pydantic import BaseModel
from app.schemas.common import ConfidenceTag, Point


class VillageSummary(BaseModel):
    village_id: str
    village_name: str
    district: str
    centroid: Point
    paddy_area_ha: float
    harvest_status: Literal["GROWING", "READY_SOON", "HARVESTED"]
    expected_harvest_date: date
    expected_straw_tonnes: float
    confidence: ConfidenceTag
'''

files["decision.py"] = '''from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel


class OptionValue(BaseModel):
    gain: float
    cost: float
    net: float


class PerTonne(BaseModel):
    keep: OptionValue
    sell: OptionValue
    feed: OptionValue


class PriceRange(BaseModel):
    low: float
    high: float


class Assumptions(BaseModel):
    fertilizer_value_per_tonne: float
    baling_cost_per_tonne: float
    transport_cost_per_tonne_per_km: float
    distance_km: float
    diesel_price_per_litre: float


class DecisionConfidence(BaseModel):
    tag: Literal["LOW", "MEDIUM", "HIGH"]
    reasons: List[str]


class Decision(BaseModel):
    village_id: str
    per_tonne_inr: PerTonne
    best_option: Literal["keep", "sell", "feed"]
    break_even_price_per_tonne_inr: float
    price_range_inr: PriceRange
    assumptions: Assumptions
    confidence: DecisionConfidence
    generated_at: datetime
'''

files["match.py"] = '''from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel


class BuyerRef(BaseModel):
    id: str
    name: str
    type: Literal["POWER", "PELLET", "BIOGAS", "OTHER"]
    distance_km: float


class IdRef(BaseModel):
    id: str


class Match(BaseModel):
    match_id: str
    village_id: str
    status: Literal["PROPOSED", "CONFIRMED", "COMPLETED", "CANCELLED"]
    tonnes: float
    buyer: BuyerRef
    baler: IdRef
    truck: IdRef
    pickup_date: date
    price_per_tonne_inr: float
    net_to_farmers_inr: float
    saving_vs_burning_note: str
    created_at: datetime
'''

files["burn.py"] = '''from datetime import date
from pydantic import BaseModel
from app.schemas.common import ConfidenceTag, Point


class Evidence(BaseModel):
    fire_points: int
    burn_scar_detected: bool
    burn_area_ha: float


class BurnEvent(BaseModel):
    event_id: str
    village_id: str
    location: Point
    detected_on: date
    confidence: ConfidenceTag
    evidence: Evidence
    source: str
'''

for name, content in files.items():
    (SCHEMAS / name).write_text(content, encoding="utf-8")
    print("written:", name)