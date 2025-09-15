from __future__ import annotations

import asyncio
import logging
from datetime import date

import httpx

from sidetrack.services.lastfm import LastfmClient
from sidetrack.api.db import SessionLocal
from sidetrack.api.main import aggregate_weeks as aggregate_weeks_service
from sidetrack.services.listens import get_listen_service
from sidetrack.common.models import Feature, Track
from sidetrack.services.datasync import sync_user as datasync_sync_user
from sidetrack.services.insights import compute_weekly_insights
from sidetrack.services.listenbrainz import ListenBrainzClient
from sidetrack.services.musicbrainz import MusicBrainzService

# Heavy numerical deps are imported lazily inside functions to keep
# API-only environments lightweight when importing this module.
from sidetrack.services.spotify import SpotifyClient
from sidetrack.extraction import compute_embeddings

from .config import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("worker")


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


async def _sync_user_service(user_id: str, since: date | None, db) -> None:
    settings = get_settings()
    listen_service = get_listen_service(db)
    rate = settings.lastfm_rate_limit or 5.0
    min_interval = 1.0 / rate if rate > 0 else 0.0
    async with (
        httpx.AsyncClient() as lb_http,
        httpx.AsyncClient() as lf_http,
        httpx.AsyncClient() as sp_http,
        httpx.AsyncClient() as mb_http,
    ):
        clients = [
            SpotifyClient(sp_http, settings.spotify_client_id, settings.spotify_client_secret),
            LastfmClient(
                lf_http,
                settings.lastfm_api_key,
                settings.lastfm_api_secret,
                min_interval=min_interval,
            ),
            ListenBrainzClient(lb_http),
        ]
        mb_service = MusicBrainzService(mb_http)
        await datasync_sync_user(
            user_id,
            db=db,
            listen_service=listen_service,
            clients=clients,
            mb_service=mb_service,
            settings=settings,
            since=since,
        )


async def _aggregate_weeks_service(user_id: str, _since: date | None, db) -> None:
    await aggregate_weeks_service(db=db, user_id=user_id)


def sync_user(user_id: str, cursor: str | None = None) -> None:
    since = date.fromisoformat(cursor) if cursor else None

    async def runner() -> None:
        async with SessionLocal() as db:
            await _sync_user_service(user_id, since, db)

    asyncio.run(runner())


def aggregate_weeks(user_id: str, cursor: str | None = None) -> None:
    async def runner() -> None:
        async with SessionLocal() as db:
            await _aggregate_weeks_service(user_id, None, db)

    asyncio.run(runner())


def generate_weekly_insights(user_id: str) -> int:
    """Compute weekly insights for ``user_id`` and return number of events."""

    async def _run() -> int:
        async with SessionLocal(async_session=True) as db:
            events = await compute_weekly_insights(db, user_id)
            return len(events)

    return asyncio.run(_run())
