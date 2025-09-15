"""Background job implementations for the worker service."""

from __future__ import annotations

import logging

# Heavy numerical deps are imported lazily inside functions to keep
# API-only environments lightweight when importing this module.
from sidetrack.services.spotify import SpotifyClient
from sidetrack.api.db import SessionLocal
from sidetrack.common.models import Feature, Track
from sidetrack.services.insights import compute_weekly_insights

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("worker")


def compute_embeddings(data: list[float]) -> list[float]:
    """Compute a simple normalised embedding vector.

    Normalisation is performed by dividing each value by the largest absolute
    value in ``data`` so that the output preserves the sign of the original
    values while remaining within ``[-1, 1]``.

    Args:
        data: List of floats representing raw features.

    Returns:
        A list of floats normalised by the maximum absolute value.
    """
    if not data:
        return []
    max_val = max(abs(x) for x in data)
    if max_val == 0:
        return [0 for _ in data]
    embeddings = [round(x / max_val, 4) for x in data]
    logger.info("computed embeddings")
    return embeddings


KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


async def fetch_spotify_features(track_id: int, access_token: str, client: SpotifyClient) -> int:
    """Fetch Spotify audio features and store them as :class:`Feature`."""

    async with SessionLocal() as db:
        track = await db.get(Track, track_id)
        if not track or not track.spotify_id:
            raise ValueError("track missing")

        data = await client.get_audio_features(access_token, track.spotify_id)

        key_name = None
        key_val = data.get("key")
        if key_val is not None and 0 <= int(key_val) < len(KEYS):
            mode = data.get("mode")
            suffix = "major" if int(mode or 1) == 1 else "minor"
            key_name = f"{KEYS[int(key_val)]} {suffix}"

        feature = Feature(
            track_id=track_id,
            bpm=data.get("tempo"),
            key=key_name,
            pumpiness=data.get("energy"),
        )
        db.add(feature)
        await db.flush()
        fid = feature.id
        await db.commit()
        return fid


def generate_weekly_insights(user_id: str) -> int:
    """Compute weekly insights for ``user_id`` and return number of events."""

    import asyncio

    async def _run() -> int:
        async with SessionLocal(async_session=True) as db:
            events = await compute_weekly_insights(db, user_id)
            return len(events)

    return asyncio.run(_run())
