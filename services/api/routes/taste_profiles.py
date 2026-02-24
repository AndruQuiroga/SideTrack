from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.db import get_db
from services.api.models import TasteProfile, User
from services.api.queue import get_queue
from services.api.schemas import TasteProfileRead

router = APIRouter(prefix="/users/{user_id}/taste-profiles", tags=["taste-profiles"])


class RecomputeAccepted(BaseModel):
    job_id: str
    status: str = "queued"
    detail: str = "Taste profile recomputation enqueued."


def _ensure_user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/", response_model=list[TasteProfileRead])
async def list_taste_profiles(
    user_id: UUID, db: Session = Depends(get_db)
) -> list[TasteProfileRead]:
    """Return stored taste profiles for a user."""

    _ensure_user(db, user_id)
    profiles = db.scalars(select(TasteProfile).where(TasteProfile.user_id == user_id)).all()
    return profiles


@router.post(
    "/recompute",
    response_model=RecomputeAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def recompute_taste_profile(
    user_id: UUID, scope: str = "all_time", db: Session = Depends(get_db)
) -> RecomputeAccepted:
    """Enqueue a taste profile recomputation for the user.

    Returns 202 with a job_id. Poll GET /jobs/{job_id}/status for progress.
    """

    _ensure_user(db, user_id)

    queue = get_queue()
    job = queue.enqueue(
        "services.api.jobs.job_recompute_taste_profile",
        str(user_id),
        scope,
        job_timeout="5m",
    )

    return RecomputeAccepted(job_id=job.id)
