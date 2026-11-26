"""Background job request / status shapes."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class JobTriggerRequest(BaseModel):
    job: Literal["refresh_forecasts", "run_matching", "daily_refresh"]
    village_id: str | None = None   # scope to one village (optional)


class JobStatusResponse(BaseModel):
    run_id: str
    job: str
    status: Literal["queued", "running", "done", "failed"]
    started_at: datetime | None
    finished_at: datetime | None
    result: dict | None
    error: str | None
