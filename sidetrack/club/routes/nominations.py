"""Nomination endpoints backed by the SQLAlchemy models."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from sidetrack.club.models import Nomination
from sidetrack.db import get_db
from sidetrack.schemas import NominationRead, NominationUpdate

router = APIRouter(prefix="/nominations", tags=["nominations"])


@router.get("/", response_model=list[NominationRead])
async def list_nominations(
    db: Session = Depends(get_db),
    week_id: UUID | None = Query(None),
    user_id: UUID | None = Query(None),
    album_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of nominations to return."),
    offset: int = Query(0, ge=0, description="Number of nominations to skip."),
) -> list[NominationRead]:
    """Return nominations, optionally filtered by week, user, or album."""

    query = select(Nomination)
    if week_id is not None:
        query = query.where(Nomination.week_id == week_id)
    if user_id is not None:
        query = query.where(Nomination.user_id == user_id)
    if album_id is not None:
        query = query.where(Nomination.album_id == album_id)

    nominations = db.execute(query.offset(offset).limit(limit)).scalars().all()
    return [NominationRead.model_validate(n) for n in nominations]


@router.get("/{nomination_id}", response_model=NominationRead)
async def get_nomination(nomination_id: UUID, db: Session = Depends(get_db)) -> NominationRead:
    """Return a single nomination by ID."""

    nomination = db.get(Nomination, nomination_id)
    if not nomination:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nomination not found.")
    return NominationRead.model_validate(nomination)


@router.patch("/{nomination_id}", response_model=NominationRead)
async def update_nomination(
    nomination_id: UUID,
    payload: NominationUpdate,
    db: Session = Depends(get_db),
) -> NominationRead:
    """Update a nomination's pitch, pitch track, tags, or album.

    Only fields included in the request body are updated.
    """
    nomination = db.get(Nomination, nomination_id)
    if not nomination:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nomination not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(nomination, field, value)

    db.commit()
    db.refresh(nomination)
    return NominationRead.model_validate(nomination)


@router.delete("/{nomination_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_nomination(
    nomination_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    """Withdraw (delete) a nomination. Cascades to associated votes."""

    nomination = db.get(Nomination, nomination_id)
    if not nomination:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nomination not found.")

    db.delete(nomination)
    db.commit()
