from typing import List, Literal
from pydantic import BaseModel

ConfidenceTag = Literal["LOW", "MEDIUM", "HIGH"]


class Point(BaseModel):
    type: Literal["Point"]
    coordinates: List[float]
