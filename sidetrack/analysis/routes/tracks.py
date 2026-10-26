"""Track and audio feature endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from sidetrack.analysis.models import TrackFeature
from sidetrack.catalog import Track
from sidetrack.db import get_db
from sidetrack.identity import auth, policy
from sidetrack.schemas.core import TrackFeatureCreate, TrackFeatureRead, TrackRead

# No client holds analysis:write today (ADR 0009); the GPU worker calls code directly.
router = APIRouter(
    prefix="/tracks", tags=["tracks"], dependencies=[Depends(policy(auth.ANALYSIS_WRITE))]
)


@router.get("/pending-features", response_model=list[TrackRead])
async def list_tracks_pending_features(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[TrackRead]:
    """Return tracks that have a spotify_id but no audio feature data yet."""

    stmt = (
        select(Track)
        .outerjoin(TrackFeature, Track.id == TrackFeature.track_id)
        .where(Track.spotify_id.is_not(None))
        .where(TrackFeature.track_id.is_(None))
        .limit(limit)
    )
    return db.scalars(stmt).all()


@router.post("/{track_id}/features", response_model=TrackFeatureRead)
async def upsert_track_features(
    track_id: UUID,
    payload: TrackFeatureCreate,
    db: Session = Depends(get_db),
) -> TrackFeatureRead:
    """Upsert Spotify audio features for a track."""

    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found.")

    features = track.features
    if features:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(features, field, value)
    else:
        features = TrackFeature(track_id=track_id, **payload.model_dump())
        db.add(features)

    db.commit()
    db.refresh(features)
    return features
