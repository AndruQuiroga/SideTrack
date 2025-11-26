"""Nomination endpoints with static responses."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.schemas.core import Nomination

router = APIRouter(prefix="/nominations", tags=["nominations"])


@router.get("/", response_model=list[Nomination])
async def list_nominations(db: Session = Depends(get_db)) -> list[Nomination]:
    """Return placeholder nominations."""

    _ = db
    return [
        Nomination(
            id=10,
            week_id=1,
            user_id="user-001",
            album_title="Discovery",
            artist_name="Daft Punk",
            album_year=2001,
            notes="A classic electronic record",
            submitted_at=datetime(2024, 6, 30, 12, 0, tzinfo=timezone.utc),
        )
    ]


@router.get("/{nomination_id}", response_model=Nomination)
async def get_nomination(nomination_id: int, db: Session = Depends(get_db)) -> Nomination:
    """Return a single nomination placeholder."""

    _ = db
    return Nomination(
        id=nomination_id,
        week_id=1,
        user_id="user-002",
        album_title="Random Access Memories",
        artist_name="Daft Punk",
        album_year=2013,
        notes="Placeholder nomination",
        submitted_at=datetime(2024, 6, 30, 13, 0, tzinfo=timezone.utc),
    )
