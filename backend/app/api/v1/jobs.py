"""
Background job trigger + status.
  POST /jobs/run      – enqueue a job (officer only)
  GET  /jobs/{run_id} – check status

When DEMO_MODE=true or Celery is unavailable the job runs synchronously
(in-process) so the demo never breaks.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import OfficerUser
from app.core.errors import not_found
from app.schemas.job import JobStatusResponse, JobTriggerRequest
from app.workers import task_runner

router = APIRouter(prefix="/jobs", tags=["jobs"])

# In-memory run registry (for demo/single-process mode).
# In production Celery results backend (Redis) holds this.
_runs: dict[str, dict] = {}


@router.post("/run", response_model=JobStatusResponse, status_code=202)
def trigger_job(
    body: JobTriggerRequest,
    _user: OfficerUser,
    db: Session = Depends(get_db),
):
    run_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc)
    _runs[run_id] = {
        "run_id": run_id, "job": body.job, "status": "queued",
        "started_at": started, "finished_at": None, "result": None, "error": None,
    }

    result, error = task_runner.run(body.job, body.village_id)

    _runs[run_id].update({
        "status": "done" if error is None else "failed",
        "finished_at": datetime.now(timezone.utc),
        "result": result,
        "error": error,
    })
    return _runs[run_id]


@router.get("/{run_id}", response_model=JobStatusResponse)
def job_status(run_id: str, _user: OfficerUser):
    entry = _runs.get(run_id)
    if entry is None:
        raise not_found("job_run", "run_id")
    return entry
