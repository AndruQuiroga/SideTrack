from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.analysis import compute_user_taste_profile
from apps.api.db import get_db
from apps.api.models import TasteProfile, User
from apps.api.schemas import TasteProfileRead

router = APIRouter(prefix="/users/{user_id}/taste-profiles", tags=["taste-profiles"])


def _ensure_user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/", response_model=list[TasteProfileRead])
async def list_taste_profiles(user_id: UUID, db: Session = Depends(get_db)) -> list[TasteProfileRead]:
    """Return stored taste profiles for a user."""

    _ensure_user(db, user_id)
    profiles = db.scalars(
        select(TasteProfile).where(TasteProfile.user_id == user_id)
    ).all()
    return profiles


@router.post(
    "/recompute",
    response_model=TasteProfileRead,
    status_code=status.HTTP_201_CREATED,
)
async def recompute_taste_profile(
    user_id: UUID, scope: str = "all_time", db: Session = Depends(get_db)
) -> TasteProfileRead:
    """Compute and store a fresh taste profile for the user."""

    _ensure_user(db, user_id)
    profile = compute_user_taste_profile(db, user_id=user_id, scope=scope)
    # Ensure updated_at reflects this invocation even if nothing changed
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return profile
