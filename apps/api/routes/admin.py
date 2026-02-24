"""Admin endpoints for moderator overrides."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.models import Album
from apps.api.models.club import Rating, Week
from apps.api.schemas import WeekRead

router = APIRouter(prefix="/admin", tags=["admin"])


class OverrideWinnerPayload(BaseModel):
    album_id: UUID


@router.post("/weeks/{week_id}/override-winner", response_model=WeekRead)
async def override_winner(
    week_id: UUID,
    payload: OverrideWinnerPayload,
    db: Session = Depends(get_db),
) -> WeekRead:
    """Manually set the winner album for a week, bypassing the poll result."""

    week = db.get(Week, week_id)
    if not week:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Week not found")

    album = db.get(Album, payload.album_id)
    if not album:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

    week.winner_album_id = payload.album_id
    db.commit()
    db.refresh(week)
    return week


@router.delete("/ratings/{rating_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rating(
    rating_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    """Hard-delete a rating (moderator action)."""

    rating = db.get(Rating, rating_id)
    if not rating:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rating not found")

    db.delete(rating)
    db.commit()
