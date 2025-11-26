"""Listen event endpoints with static data."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.schemas import ListenEventRead
from apps.api.models.listening import ListenSource

router = APIRouter(prefix="/listen-events", tags=["listen-events"])


@router.get("/", response_model=list[ListenEventRead])
async def list_listen_events(db: Session = Depends(get_db)) -> list[ListenEventRead]:
    """Return placeholder listen events."""

    _ = db
    return [
        ListenEventRead(
            id=uuid4(),
            user_id=uuid4(),
            track_id=uuid4(),
            played_at=datetime(2024, 7, 3, 8, 30, tzinfo=timezone.utc),
            source=ListenSource.SPOTIFY,
            metadata={"context": "morning commute"},
            ingested_at=datetime(2024, 7, 3, 8, 31, tzinfo=timezone.utc),
        )
    ]


@router.get("/{listen_event_id}", response_model=ListenEventRead)
async def get_listen_event(
    listen_event_id: UUID, db: Session = Depends(get_db)
) -> ListenEventRead:
    """Return a sample listen event."""

    _ = db
    return ListenEventRead(
        id=listen_event_id,
        user_id=uuid4(),
        track_id=uuid4(),
        played_at=datetime(2024, 7, 3, 9, 0, tzinfo=timezone.utc),
        source=ListenSource.LASTFM,
        metadata={"source": "backfill"},
        ingested_at=datetime(2024, 7, 3, 9, 2, tzinfo=timezone.utc),
    )
