"""Rating endpoints emitting placeholder content."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.schemas import RatingRead

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.get("/", response_model=list[RatingRead])
async def list_ratings(db: Session = Depends(get_db)) -> list[RatingRead]:
    """Return static ratings."""

    _ = db
    return [
        RatingRead(
            id=uuid4(),
            week_id=uuid4(),
            nomination_id=uuid4(),
            user_id=uuid4(),
            album_id=uuid4(),
            value=4.5,
            review="Great pick!",
            favorite_track="Face to Face",
            created_at=datetime(2024, 7, 2, 18, 0, tzinfo=timezone.utc),
        )
    ]


@router.get("/{rating_id}", response_model=RatingRead)
async def get_rating(rating_id: UUID, db: Session = Depends(get_db)) -> RatingRead:
    """Return a placeholder rating payload."""

    _ = db
    return RatingRead(
        id=rating_id,
        week_id=uuid4(),
        nomination_id=uuid4(),
        user_id=uuid4(),
        album_id=uuid4(),
        value=3.5,
        review="Solid listen.",
        favorite_track="Fragments of Time",
        created_at=datetime(2024, 7, 2, 19, 0, tzinfo=timezone.utc),
    )
