"""Routes to trigger external ingestion jobs (MVP: Last.fm).

Ingestion runs asynchronously in Postgres. POST returns 202 with a job_id;
callers can poll GET /jobs/{job_id}/status for progress.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from procrastinate.exceptions import ProcrastinateException
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from sidetrack.db import get_db
from sidetrack.identity import Principal, User, auth, policy
from sidetrack.queue_client import enqueue

router = APIRouter(prefix="/ingest", tags=["ingest"])


class LastfmIngestRequest(BaseModel):
    # Deprecated: the acting user is imported; a different value is refused.
    user_id: UUID | None = None
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
    principal: Principal = Depends(policy(auth.PERSONAL_WRITE)),
) -> JobAccepted:
    """Enqueue a Last.fm scrobble ingest for the acting user."""

    user_id = auth.resolve_owner(principal, payload.user_id)
    try:
        if not db.get(User, user_id):
            raise HTTPException(status_code=404, detail="User not found")
        job = enqueue(
            db,
            "listening.ingest_lastfm",
            {
                "user_id": str(user_id),
                "lastfm_username": payload.lastfm_username,
                "since_ts": payload.since_ts,
            },
            requested_by=user_id,
        )
        public_id = str(job.id)
        db.commit()
    except (SQLAlchemyError, ProcrastinateException):
        db.rollback()
        raise HTTPException(status_code=503, detail="Job queue unavailable") from None
    return JobAccepted(job_id=public_id)
