"""
Background job trigger + status.
  POST /jobs/run      – enqueue a job (officer only)
  GET  /jobs/{run_id} – check status (officer only)

In production: Celery tasks are dispatched to Redis; job metadata (`job`,
`started_at`, `finished_at`) is stored in Redis under `rc:job:{run_id}` so
GET /jobs/{run_id} returns 404 for unknown IDs, preserves job name and
timestamps, and maps Celery states cleanly to the JobStatusResponse schema.

In demo / no-Redis mode: job runs synchronously in-process and stores state
in `_sync_runs`.
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import OfficerUser
from app.core.errors import bad_request, not_found
from app.schemas.job import JobStatusResponse, JobTriggerRequest
from app.workers import task_runner

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger("jobs")

_JOB_TTL_SECONDS = 7 * 86400
_sync_runs: dict[str, dict] = {}


def _redis_client():
    try:
        import redis  # type: ignore
        return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        return None


def _save_job_meta(run_id: str, meta: dict) -> None:
    client = _redis_client()
    if client is not None:
        try:
            client.setex(f"rc:job:{run_id}", _JOB_TTL_SECONDS, json.dumps(meta))
            return
        except Exception:
            logger.debug("Redis metadata write failed; falling back to in-memory store")
    _sync_runs[run_id] = meta


def _load_job_meta(run_id: str) -> Optional[dict]:
    if run_id in _sync_runs:
        return _sync_runs[run_id]
    client = _redis_client()
    if client is not None:
        try:
            raw = client.get(f"rc:job:{run_id}")
            if raw:
                return json.loads(raw)
        except Exception:
            logger.debug("Redis metadata read failed")
    return None


def _celery_state_to_schema(result: Any, meta: dict) -> dict:
    """
    Map a Celery AsyncResult + stored metadata to JobStatusResponse.
    Only emits schema-valid states: queued | running | done | failed | cancelled.
    """
    state_map = {
        "PENDING": "queued",
        "RECEIVED": "queued",
        "STARTED": "running",
        "RETRY":   "running",
        "SUCCESS": "done",
        "FAILURE": "failed",
        "REVOKED": "cancelled",
    }
    status = state_map.get(result.state, "failed")
    output = result.result if result.state == "SUCCESS" else None
    error  = str(result.result) if result.state == "FAILURE" else None

    finished_at = meta.get("finished_at")
    if status in ("done", "failed", "cancelled") and finished_at is None:
        finished_at = datetime.now(timezone.utc).isoformat()
        meta["finished_at"] = finished_at
        _save_job_meta(result.id, meta)

    return {
        "run_id":      result.id,
        "job":         meta["job"],
        "status":      status,
        "started_at":  meta.get("started_at"),
        "finished_at": finished_at,
        "result":      output,
        "error":       error,
    }


@router.post("/run", response_model=JobStatusResponse, status_code=202)
def trigger_job(
    body: JobTriggerRequest,
    _user: OfficerUser,
    db: Session = Depends(get_db),
):
    """Enqueue a named background job."""
    use_celery = (
        task_runner.CELERY_AVAILABLE
        and not task_runner.settings.DEMO_MODE
    )

    if use_celery:
        task = task_runner.dispatch_async(body.job, body.village_id)
        if task is None:
            raise bad_request(f"Unknown job: {body.job}", "job")
        started = datetime.now(timezone.utc)
        meta = {
            "run_id":      task.id,
            "job":         body.job,
            "status":      "queued",
            "started_at":  started.isoformat(),
            "finished_at": None,
            "result":      None,
            "error":       None,
        }
        _save_job_meta(task.id, meta)
        return meta

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
    Poll the status of a background job by its run_id.
    Returns 404 if run_id was never recorded by this service.
    """
    meta = _load_job_meta(run_id)
    if meta is None:
        raise not_found("job_run", "run_id")

    # Sync / demo runs already contain full final state
    if meta.get("status") in ("done", "failed", "cancelled") and not (
        task_runner.CELERY_AVAILABLE and not task_runner.settings.DEMO_MODE
    ):
        return meta

    if task_runner.CELERY_AVAILABLE and task_runner._celery_app:
        from celery.result import AsyncResult  # type: ignore
        result = AsyncResult(run_id, app=task_runner._celery_app)
        return _celery_state_to_schema(result, meta)

    return meta
