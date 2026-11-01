"""Forgotten favourites and their dismissals. Owner only, whatever the sharing setting."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sidetrack.catalog import Track
from sidetrack.db import get_db
from sidetrack.identity import Principal, auth, policy
from sidetrack.listening.rediscovery import (
    TrackUnavailable,
    clear_dismissals,
    dismiss,
    forgotten_favourites,
    list_dismissals,
    remove_dismissal,
)

router = APIRouter(prefix="/users", tags=["listening"])


class RuleValues(BaseModel):
    rule_version: str
    min_plays: int
    window_days: int
    forgotten_days: int
    min_recent_plays: int
    min_recent_days: int


class ForgottenTrack(BaseModel):
    track_id: UUID
    title: str
    artist_name: str
    peak_plays: int
    peak_start: datetime
    peak_end: datetime
    last_played_at: datetime
    total_plays: int


class RediscoveryRead(BaseModel):
    state: Literal["found", "none_found", "not_imported", "coverage_gap", "insufficient_history"]
    rules: RuleValues
    include_autoplay: bool
    coverage_start: datetime | None
    coverage_end: datetime | None
    recent_plays: int | None
    recent_days: int | None
    excluded_autoplay_plays: int
    unknown_session_plays: int
    dismissed_hidden: int
    tracks: list[ForgottenTrack]


class DismissalWrite(BaseModel):
    reason: Literal["not_a_favourite", "not_now"]


class DismissalRead(BaseModel):
    track_id: UUID
    title: str | None
    artist_name: str | None
    reason: str
    created_at: datetime


@router.get("/{user_id}/listening/rediscovery", response_model=RediscoveryRead)
def read_rediscovery(
    user_id: UUID,
    include_autoplay: bool = Query(False),
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.PERSONAL_READ)),
) -> dict:
    auth.require_self(principal, user_id)
    return forgotten_favourites(db, user_id, include_autoplay=include_autoplay)


@router.get("/{user_id}/listening/rediscovery/dismissals", response_model=list[DismissalRead])
def read_dismissals(
    user_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.PERSONAL_READ)),
) -> list[DismissalRead]:
    auth.require_self(principal, user_id)
    return [_read(*row) for row in list_dismissals(db, user_id)]


@router.put("/{user_id}/listening/rediscovery/dismissals/{track_id}", response_model=DismissalRead)
def put_dismissal(
    user_id: UUID,
    track_id: UUID,
    payload: DismissalWrite,
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.PERSONAL_WRITE)),
) -> DismissalRead:
    auth.require_self(principal, user_id)
    try:
        row = dismiss(db, user_id, track_id, payload.reason)
    except TrackUnavailable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found") from None
    db.commit()
    return _read(row, db.get(Track, track_id))


@router.delete(
    "/{user_id}/listening/rediscovery/dismissals/{track_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_dismissal(
    user_id: UUID,
    track_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.PERSONAL_WRITE)),
) -> Response:
    auth.require_self(principal, user_id)
    if not remove_dismissal(db, user_id, track_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{user_id}/listening/rediscovery/dismissals", status_code=status.HTTP_204_NO_CONTENT
)
def delete_dismissals(
    user_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.PERSONAL_WRITE)),
) -> Response:
    auth.require_self(principal, user_id)
    clear_dismissals(db, user_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _read(row, track) -> DismissalRead:
    return DismissalRead(
        track_id=UUID(row.track_key),
        title=track.title if track else None,
        artist_name=track.artist_name if track else None,
        reason=row.reason,
        created_at=row.created_at,
    )
