"""Vote endpoints returning placeholder data."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.schemas import VoteRead

router = APIRouter(prefix="/votes", tags=["votes"])


@router.get("/", response_model=list[VoteRead])
async def list_votes(db: Session = Depends(get_db)) -> list[VoteRead]:
    """Return static votes for now."""

    _ = db
    return [
        VoteRead(
            id=uuid4(),
            week_id=uuid4(),
            nomination_id=uuid4(),
            user_id=uuid4(),
            rank=1,
            submitted_at=datetime(2024, 7, 1, 9, 30, tzinfo=timezone.utc),
        )
    ]


@router.get("/{vote_id}", response_model=VoteRead)
async def get_vote(vote_id: UUID, db: Session = Depends(get_db)) -> VoteRead:
    """Return a sample vote payload."""

    _ = db
    return VoteRead(
        id=vote_id,
        week_id=uuid4(),
        nomination_id=uuid4(),
        user_id=uuid4(),
        rank=2,
        submitted_at=datetime(2024, 7, 1, 10, 0, tzinfo=timezone.utc),
    )
