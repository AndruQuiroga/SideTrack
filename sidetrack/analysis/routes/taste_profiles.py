from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from procrastinate.exceptions import ProcrastinateException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from sidetrack.analysis.models import TasteProfile
from sidetrack.db import get_db
from sidetrack.identity import User
from sidetrack.queue_client import enqueue
from sidetrack.schemas import TasteProfileRead

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

    try:
        _ensure_user(db, user_id)
        job = enqueue(
            db,
            "analysis.recompute_taste_profile",
            {
                "user_id": str(user_id),
                "scope": scope,
            },
        )
        public_id = str(job.id)
        db.commit()
    except (SQLAlchemyError, ProcrastinateException):
        db.rollback()
        raise HTTPException(status_code=503, detail="Job queue unavailable") from None
    return RecomputeAccepted(job_id=public_id)
