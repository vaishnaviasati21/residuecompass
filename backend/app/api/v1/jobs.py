"""
Background job trigger + status.
  POST /jobs/run      – enqueue a job (officer only)
  GET  /jobs/{run_id} – check status (officer only)

In production: Celery tasks are dispatched to Redis; GET polls AsyncResult.
In demo / no-Redis mode: job runs synchronously in-process; a synthetic run_id
is generated and the result is returned immediately.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import OfficerUser
from app.core.errors import not_found
from app.schemas.job import JobStatusResponse, JobTriggerRequest
from app.workers import task_runner

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Fallback in-memory store for demo / single-process mode.
# In production Celery's Redis results backend holds all state.
_sync_runs: dict[str, dict] = {}


def _celery_state_to_schema(result: Any, job: str) -> dict:
    """
    Map a Celery AsyncResult to our JobStatusResponse dict.
    Celery states: PENDING → queued, STARTED → running,
                   SUCCESS → done, FAILURE → failed, REVOKED → cancelled.
    """
    state_map = {
        "PENDING": "queued",
        "STARTED": "running",
        "SUCCESS": "done",
        "FAILURE": "failed",
        "REVOKED": "cancelled",
        "RETRY":   "running",
    }
    status = state_map.get(result.state, "unknown")
    output = None
    error  = None

    if result.state == "SUCCESS":
        output = result.result
    elif result.state == "FAILURE":
        error = str(result.result)

    return {
        "run_id":      result.id,
        "job":         job,
        "status":      status,
        "started_at":  None,   # Celery doesn't expose this without a custom backend
        "finished_at": None,
        "result":      output,
        "error":       error,
    }


@router.post("/run", response_model=JobStatusResponse, status_code=202)
def trigger_job(
    body: JobTriggerRequest,
    _user: OfficerUser,
    db: Session = Depends(get_db),
):
    """
    Enqueue a named background job.

    When Celery + Redis are available (production): dispatches async and
    returns immediately with status='queued' and the Celery task ID.
    GET /jobs/{run_id} can then be polled for real state.

    When running in demo mode or Redis is unavailable: runs synchronously
    in-process and returns the finished result in the same response.
    """
    use_celery = (
        task_runner.CELERY_AVAILABLE
        and not task_runner.settings.DEMO_MODE
    )

    if use_celery:
        task = task_runner.dispatch_async(body.job, body.village_id)
        if task is None:
            # Unknown job – dispatch_async returns None for bad names
            from app.core.errors import bad_request
            raise bad_request(f"Unknown job: {body.job}", "job")
        return {
            "run_id":      task.id,
            "job":         body.job,
            "status":      "queued",
            "started_at":  datetime.now(timezone.utc),
            "finished_at": None,
            "result":      None,
            "error":       None,
        }

    # Synchronous / demo path
    run_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc)
    result, error = task_runner.run(body.job, body.village_id)
    entry = {
        "run_id":      run_id,
        "job":         body.job,
        "status":      "done" if error is None else "failed",
        "started_at":  started,
        "finished_at": datetime.now(timezone.utc),
        "result":      result,
        "error":       error,
    }
    _sync_runs[run_id] = entry
    return entry


@router.get("/{run_id}", response_model=JobStatusResponse)
def job_status(run_id: str, _user: OfficerUser):
    """
    Poll the status of a background job by its run_id (Celery task ID or
    synthetic UUID from sync/demo mode).
    """
    # Check in-memory store first (demo / sync runs)
    if run_id in _sync_runs:
        return _sync_runs[run_id]

    # Try Celery Redis backend
    if task_runner.CELERY_AVAILABLE and task_runner._celery_app:
        from celery.result import AsyncResult  # type: ignore
        result = AsyncResult(run_id, app=task_runner._celery_app)
        # PENDING is returned for unknown IDs too; we can't distinguish,
        # so return it as-is (callers should use the ID returned from POST /run).
        # Determine which job name to show – not stored in Celery result metadata
        # unless the task sets it; fall back to "unknown".
        job_name = "unknown"
        if result.state == "SUCCESS" and isinstance(result.result, dict):
            job_name = result.result.get("job", "unknown")
        return _celery_state_to_schema(result, job_name)

    raise not_found("job_run", "run_id")
