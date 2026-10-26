"""Job status endpoint for polling background job progress."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from sidetrack.db import get_db
from sidetrack.identity import Principal, auth, policy
from sidetrack.queue_models import BackgroundJob

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: Any | None = None
    error: str | None = None


@router.get("/{job_id}/status", response_model=JobStatus)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.PERSONAL_READ)),
) -> JobStatus:
    """Poll the status of a background job.

    Possible status values: queued, started, finished, failed, deferred, canceled.
    """
    try:
        uid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found") from None
    job = db.get(BackgroundJob, uid)
    # Only the submitter may poll; jobs nobody submitted are hidden too.
    if (
        job is None
        or job.requested_by_user_id is None
        or job.requested_by_user_id != principal.actor
    ):
        raise HTTPException(status_code=404, detail="Job not found")
    queue_status = db.execute(
        text(
            "SELECT status::text, scheduled_at > clock_timestamp() AS deferred "
            "FROM job_queue.procrastinate_jobs WHERE id=:id"
        ),
        {"id": job.queue_job_id},
    ).first()
    state = job.status
    if state != "finished" and queue_status:
        raw, deferred = queue_status
        state = {
            "doing": "started",
            "succeeded": "finished",
            "failed": "failed",
            "cancelled": "canceled",
            "aborted": "failed",
        }.get(raw, "deferred" if deferred or job.attempts else "queued")
    return JobStatus(
        job_id=job_id,
        status=state,
        result=job.result if state == "finished" else None,
        error=(job.error or "execution_failed") if state == "failed" else None,
    )
