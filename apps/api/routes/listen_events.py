"""Listen event endpoints with persistence and basic filters."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.models import ListenEvent, ListenSource, Track, User
from apps.api.schemas import ListenEventCreate, ListenEventRead

router = APIRouter(prefix="/listen-events", tags=["listen-events"])


class ListenEventsPayload(BaseModel):
    listens: list[ListenEventCreate] = Field(..., description="Listen events to upsert.")


def _find_existing(
    db: Session, user_id: UUID, track_id: UUID, played_at: datetime
) -> ListenEvent | None:
    stmt = select(ListenEvent).where(
        ListenEvent.user_id == user_id,
        ListenEvent.track_id == track_id,
        ListenEvent.played_at == played_at,
    )
    return db.scalars(stmt).first()


def _ensure_user_and_track(db: Session, user_id: UUID, track_id: UUID) -> None:
    if not db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not db.get(Track, track_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")


@router.get("/", response_model=list[ListenEventRead])
async def list_listen_events(
    db: Session = Depends(get_db),
    user_id: UUID | None = Query(None, description="Filter listen events by user."),
    source: ListenSource | None = Query(None, description="Filter by listen source."),
    played_after: datetime | None = Query(None, description="Return listens played at/after this time."),
    played_before: datetime | None = Query(None, description="Return listens played at/before this time."),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of events to return."),
) -> list[ListenEventRead]:
    """Return persisted listen events, newest first."""

    query = select(ListenEvent)
    if user_id:
        query = query.where(ListenEvent.user_id == user_id)
    if source:
        query = query.where(ListenEvent.source == source)
    if played_after:
        query = query.where(ListenEvent.played_at >= played_after)
    if played_before:
        query = query.where(ListenEvent.played_at <= played_before)

    listens = (
        db.execute(
            query.order_by(ListenEvent.played_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )
    return listens


@router.get("/{listen_event_id}", response_model=ListenEventRead)
async def get_listen_event(
    listen_event_id: UUID, db: Session = Depends(get_db)
) -> ListenEventRead:
    """Return a single listen event."""

    listen = db.get(ListenEvent, listen_event_id)
    if not listen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listen event not found")
    return listen


@router.post("/", response_model=list[ListenEventRead], status_code=status.HTTP_201_CREATED)
async def upsert_listen_events(
    payload: ListenEventsPayload, db: Session = Depends(get_db)
) -> list[ListenEventRead]:
    """Upsert listen events; duplicates (user, track, played_at) are returned without creating new rows."""

    ingested_at = datetime.now(timezone.utc)
    stored: list[ListenEvent] = []

    for listen in payload.listens:
        _ensure_user_and_track(db, listen.user_id, listen.track_id)
        existing = _find_existing(db, listen.user_id, listen.track_id, listen.played_at)
        if existing:
            stored.append(existing)
            continue

        listen_data = listen.model_dump()
        listen_data["metadata_"] = listen_data.pop(
            "metadata", listen_data.pop("metadata_", None)
        )
        listen_data["ingested_at"] = ingested_at
        record = ListenEvent(**listen_data)
        db.add(record)
        stored.append(record)

    db.commit()
    for record in stored:
        db.refresh(record)

    return stored
