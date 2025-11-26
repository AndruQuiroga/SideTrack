"""Rating endpoints emitting placeholder content."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.schemas.core import Rating

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.get("/", response_model=list[Rating])
async def list_ratings(db: Session = Depends(get_db)) -> list[Rating]:
    """Return static ratings."""

    _ = db
    return [
        Rating(
            id=200,
            week_id=1,
            nomination_id=10,
            user_id="user-005",
            score=4.5,
            review="Great pick!",
            favorite_track="Face to Face",
            created_at=datetime(2024, 7, 2, 18, 0, tzinfo=timezone.utc),
        )
    ]


@router.get("/{rating_id}", response_model=Rating)
async def get_rating(rating_id: int, db: Session = Depends(get_db)) -> Rating:
    """Return a placeholder rating payload."""

    _ = db
    return Rating(
        id=rating_id,
        week_id=1,
        nomination_id=11,
        user_id="user-006",
        score=3.5,
        review="Solid listen.",
        favorite_track="Fragments of Time",
        created_at=datetime(2024, 7, 2, 19, 0, tzinfo=timezone.utc),
    )
