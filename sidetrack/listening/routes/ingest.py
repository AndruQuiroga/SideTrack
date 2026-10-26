"""Routes to trigger external ingestion jobs (MVP: Last.fm).

Ingestion runs asynchronously via RQ. POST returns 202 with a job_id;
callers can poll GET /jobs/{job_id}/status for progress.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sidetrack.db import get_db
from sidetrack.identity import User
from sidetrack.queue import get_queue

router = APIRouter(prefix="/ingest", tags=["ingest"])


class LastfmIngestRequest(BaseModel):
    user_id: UUID
    lastfm_username: str
    since_ts: int | None = None


class JobAccepted(BaseModel):
    job_id: str
    status: str = "queued"
    detail: str = "Job enqueued for background processing."


@router.post("/lastfm", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
def trigger_lastfm_ingest(
    payload: LastfmIngestRequest,
    db: Session = Depends(get_db),
) -> JobAccepted:
    """Enqueue a Last.fm scrobble ingest for the given user."""

    # Validate user exists before queuing
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    queue = get_queue()
    job = queue.enqueue(
        "services.api.jobs.job_ingest_lastfm",
        str(payload.user_id),
        payload.lastfm_username,
        payload.since_ts,
        job_timeout="10m",
    )

    return JobAccepted(job_id=job.id)
