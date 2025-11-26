"""Week endpoints with placeholder payloads."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.schemas import WeekRead

router = APIRouter(prefix="/weeks", tags=["weeks"])


@router.get("/", response_model=list[WeekRead])
async def list_weeks(db: Session = Depends(get_db)) -> list[WeekRead]:
    """Return a static set of club weeks."""

    _ = db
    return [
        WeekRead(
            id=uuid4(),
            label="Week 1: Discovery",
            week_number=1,
            discussion_at=datetime(2024, 7, 8, 19, 0, tzinfo=timezone.utc),
            nominations_close_at=datetime(2024, 7, 1, 17, 0, tzinfo=timezone.utc),
            poll_close_at=datetime(2024, 7, 3, 17, 0, tzinfo=timezone.utc),
            winner_album_id=uuid4(),
            nominations_thread_id=123456789012345678,
            poll_thread_id=123456789012345679,
            winner_thread_id=123456789012345680,
            ratings_thread_id=123456789012345681,
            created_at=datetime(2024, 6, 30, 12, 0, tzinfo=timezone.utc),
        )
    ]


@router.get("/{week_id}", response_model=WeekRead)
async def get_week(week_id: UUID, db: Session = Depends(get_db)) -> WeekRead:
    """Return a single representative week."""

    _ = db
    return WeekRead(
        id=week_id,
        label="Week 2: Space Disco",
        week_number=2,
        discussion_at=datetime(2024, 7, 15, 19, 0, tzinfo=timezone.utc),
        nominations_close_at=datetime(2024, 7, 8, 17, 0, tzinfo=timezone.utc),
        poll_close_at=datetime(2024, 7, 10, 17, 0, tzinfo=timezone.utc),
        winner_album_id=uuid4(),
        nominations_thread_id=223456789012345678,
        poll_thread_id=223456789012345679,
        winner_thread_id=223456789012345680,
        ratings_thread_id=223456789012345681,
        created_at=datetime(2024, 7, 7, 12, 0, tzinfo=timezone.utc),
    )
