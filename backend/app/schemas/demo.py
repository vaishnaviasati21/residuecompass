"""Demo one-click loop response shape."""
from pydantic import BaseModel


class DemoLoopStep(BaseModel):
    step: str
    status: str
    detail: str | None = None


class DemoLoopResponse(BaseModel):
    village_id: str
    steps: list[DemoLoopStep]
    forecast_snapshot: dict | None
    decision_snapshot: dict | None
    match_snapshot: dict | None
    notification_body: str | None
    burn_check: dict | None
