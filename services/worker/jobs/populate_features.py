"""Populate audio features from Spotify for tracks missing them.

Replaces the TS PopulateFeaturesJob. Writes directly to the database
instead of going through the API.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.models.music import Track, TrackFeature

from ..connectors.spotify import SpotifyConnector

logger = logging.getLogger(__name__)

BATCH_SIZE = 100  # Spotify's max for the audio-features batch endpoint


async def populate_features(db: Session, spotify: SpotifyConnector, limit: int = 500) -> int:
    """Fetch audio features from Spotify for tracks that don't have them yet.

    Returns the number of tracks updated.
    """
    token = await spotify.get_client_token()
    if not token:
        logger.info("Spotify client credentials not configured; skipping feature population.")
        return 0

    # Find tracks with a spotify_id but no TrackFeature row
    stmt = (
        select(Track)
        .outerjoin(TrackFeature, Track.id == TrackFeature.track_id)
        .where(Track.spotify_id.isnot(None), TrackFeature.track_id.is_(None))
        .limit(limit)
    )
    pending = list(db.execute(stmt).scalars().all())

    if not pending:
        return 0

    logger.info("%d tracks need audio features.", len(pending))
    updated = 0

    for i in range(0, len(pending), BATCH_SIZE):
        batch = pending[i : i + BATCH_SIZE]
        spotify_ids = [t.spotify_id for t in batch if t.spotify_id]

        features = await spotify.fetch_audio_features_batch(spotify_ids, token)
        features_by_id = {f["id"]: f for f in features}

        for track in batch:
            feat = features_by_id.get(track.spotify_id)
            if not feat:
                continue

            track_feature = TrackFeature(
                track_id=track.id,
                energy=feat.get("energy"),
                valence=feat.get("valence"),
                danceability=feat.get("danceability"),
                tempo=feat.get("tempo"),
                acousticness=feat.get("acousticness"),
                instrumentalness=feat.get("instrumentalness"),
            )
            db.merge(track_feature)
            updated += 1

        db.commit()

    logger.info("Populated audio features for %d tracks.", updated)
    return updated
