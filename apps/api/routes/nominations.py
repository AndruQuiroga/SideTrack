"""Nomination endpoints with static responses."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.schemas import NominationRead

router = APIRouter(prefix="/nominations", tags=["nominations"])


@router.get("/", response_model=list[NominationRead])
async def list_nominations(db: Session = Depends(get_db)) -> list[NominationRead]:
    """Return placeholder nominations."""

    _ = db
    return [
        NominationRead(
            id=uuid4(),
            week_id=uuid4(),
            user_id=uuid4(),
            album_id=uuid4(),
            pitch="A classic electronic record everyone should revisit",
            pitch_track_url="https://open.spotify.com/track/example",
            genre_tag="electronic",
            decade_tag="2000s",
            country_tag="France",
            submitted_at=datetime(2024, 6, 30, 12, 0, tzinfo=timezone.utc),
        )
    ]


@router.get("/{nomination_id}", response_model=NominationRead)
async def get_nomination(
    nomination_id: UUID, db: Session = Depends(get_db)
) -> NominationRead:
    """Return a single nomination placeholder."""

    _ = db
    return NominationRead(
        id=nomination_id,
        week_id=uuid4(),
        user_id=uuid4(),
        album_id=uuid4(),
        pitch="A shimmering slice of nu-disco",
        pitch_track_url="https://open.spotify.com/track/another-example",
        genre_tag="disco",
        decade_tag="2010s",
        country_tag="UK",
        submitted_at=datetime(2024, 6, 30, 13, 0, tzinfo=timezone.utc),
    )
