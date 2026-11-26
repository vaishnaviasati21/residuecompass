"""
Schema code generator – EXPLICIT TOOL, NOT A BUILD STEP.

Usage:
    python scripts/make_schemas.py [--force]

This script can re-generate a subset of schema stubs from embedded templates.
It is intentionally NON-DESTRUCTIVE by default:
  - Files that already exist are SKIPPED (a warning is printed).
  - Pass --force to overwrite existing files.

The authoritative schemas are the hand-maintained files in app/schemas/.
Do NOT import this module in application code or run it as part of CI.
If you need to add a new schema, edit app/schemas/ directly.
"""
import argparse
import sys
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


def main(force: bool = False) -> None:
    written = 0
    skipped = 0
    for name, content in files.items():
        target = SCHEMAS / name
        if target.exists() and not force:
            print(f"SKIPPED (already exists): {name}  (use --force to overwrite)")
            skipped += 1
            continue
        target.write_text(content, encoding="utf-8")
        print(f"written: {name}")
        written += 1

    print(f"\n{written} file(s) written, {skipped} file(s) skipped.")
    if skipped:
        print("NOTE: hand-maintained schema files were left untouched.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing schema files (destructive!).",
    )
    args = parser.parse_args()
    main(force=args.force)
