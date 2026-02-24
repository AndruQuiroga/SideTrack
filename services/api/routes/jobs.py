"""Job status endpoint for polling background job progress."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from rq.job import Job

from services.api.queue import get_redis_connection

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: Any | None = None
    error: str | None = None


@router.get("/{job_id}/status", response_model=JobStatus)
def get_job_status(job_id: str) -> JobStatus:
    """Poll the status of a background job.

    Possible status values: queued, started, finished, failed, deferred, canceled.
    """
    conn = get_redis_connection()
    job = Job.fetch(job_id, connection=conn)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    job_status = job.get_status()

    result = None
    error = None
    if job_status == "finished":
        result = job.result
    elif job_status == "failed":
        error = str(job.exc_info) if job.exc_info else "Unknown error"

    return JobStatus(
        job_id=job_id,
        status=job_status,
        result=result,
        error=error,
    )
