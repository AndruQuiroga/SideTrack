"""Vote endpoints returning placeholder data."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.schemas.core import Vote

router = APIRouter(prefix="/votes", tags=["votes"])


@router.get("/", response_model=list[Vote])
async def list_votes(db: Session = Depends(get_db)) -> list[Vote]:
    """Return static votes for now."""

    _ = db
    return [
        Vote(
            id=100,
            nomination_id=10,
            user_id="user-003",
            rank=1,
            submitted_at=datetime(2024, 7, 1, 9, 30, tzinfo=timezone.utc),
        )
    ]


@router.get("/{vote_id}", response_model=Vote)
async def get_vote(vote_id: int, db: Session = Depends(get_db)) -> Vote:
    """Return a sample vote payload."""

    _ = db
    return Vote(
        id=vote_id,
        nomination_id=11,
        user_id="user-004",
        rank=2,
        submitted_at=datetime(2024, 7, 1, 10, 0, tzinfo=timezone.utc),
    )
