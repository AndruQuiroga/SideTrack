"""Listen event endpoints with static data."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.schemas.core import ListenEvent

router = APIRouter(prefix="/listen-events", tags=["listen-events"])


@router.get("/", response_model=list[ListenEvent])
async def list_listen_events(db: Session = Depends(get_db)) -> list[ListenEvent]:
    """Return placeholder listen events."""

    _ = db
    return [
        ListenEvent(
            id=300,
            user_id="user-007",
            track_id=12345,
            played_at=datetime(2024, 7, 3, 8, 30, tzinfo=timezone.utc),
            source="spotify",
            metadata={"context": "morning commute"},
            ingested_at=datetime(2024, 7, 3, 8, 31, tzinfo=timezone.utc),
        )
    ]


@router.get("/{listen_event_id}", response_model=ListenEvent)
async def get_listen_event(listen_event_id: int, db: Session = Depends(get_db)) -> ListenEvent:
    """Return a sample listen event."""

    _ = db
    return ListenEvent(
        id=listen_event_id,
        user_id="user-008",
        track_id=98765,
        played_at=datetime(2024, 7, 3, 9, 0, tzinfo=timezone.utc),
        source="lastfm",
        metadata={"source": "backfill"},
        ingested_at=datetime(2024, 7, 3, 9, 2, tzinfo=timezone.utc),
    )
