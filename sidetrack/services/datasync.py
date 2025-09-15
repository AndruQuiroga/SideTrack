"""Utilities for synchronising listen history and enrichment.

This module orchestrates the full data synchronisation pipeline for a user:

1. Fetch listens from external providers (Spotify, Last.fm, ListenBrainz).
2. Normalise and store listens via :class:`~sidetrack.api.services.listen_service.ListenService`.
3. Enrich tracks with tags and external identifiers.

The main entry point is :func:`sync_user` which is designed for use by the
job runner or worker processes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.api.clients.lastfm import LastfmClient
from sidetrack.api.config import Settings
from sidetrack.api.services.listen_service import ListenService
from sidetrack.common.models import Artist, Listen, Track, UserSettings
from sidetrack.services.listenbrainz import ListenBrainzClient
from sidetrack.services.musicbrainz import MusicBrainzService
from sidetrack.services.spotify import SpotifyClient


@dataclass
class SyncResult:
    """Summary of a synchronisation run."""

    ingested: int = 0
    tags_updated: int = 0
    ids_enriched: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "ingested": self.ingested,
            "tags_updated": self.tags_updated,
            "ids_enriched": self.ids_enriched,
        }


async def _fetch_listens(
    user_id: str,
    *,
    db: AsyncSession,
    listen_service: ListenService,
    lb_client: ListenBrainzClient,
    lf_client: LastfmClient,
    sp_client: SpotifyClient,
    settings: Settings,
    since: date | None = None,
) -> int:
    """Fetch and ingest recent listens for ``user_id``.

    The function mirrors the logic of the legacy ``/ingest/listens`` endpoint
    but is usable outside of the HTTP layer.
    """

    settings_row = (
        await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    ).scalar_one_or_none()

    # Spotify first
    if settings_row and settings_row.spotify_access_token:
        try:
            since_dt = datetime.combine(since, datetime.min.time()) if since else None
            items = await sp_client.fetch_recently_played(
                settings_row.spotify_access_token, after=since_dt
            )
            return await listen_service.ingest_spotify_rows(items, user_id)
        except Exception:  # pragma: no cover - network errors
            pass

    # Last.fm next
    if settings_row and settings_row.lastfm_user and settings_row.lastfm_session_key:
        try:
            since_dt = datetime.combine(since, datetime.min.time()) if since else None
            tracks = await lf_client.fetch_recent_tracks(settings_row.lastfm_user, since_dt)
            return await listen_service.ingest_lastfm_rows(tracks, user_id)
        except Exception:  # pragma: no cover - network errors
            pass

    # Fallback to ListenBrainz
    token = settings.listenbrainz_token
    lb_user = user_id
    if settings_row:
        token = settings_row.listenbrainz_token or token
        lb_user = settings_row.listenbrainz_user or lb_user
    rows = await lb_client.fetch_listens(lb_user, since, token)
    return await listen_service.ingest_lb_rows(rows, user_id)


async def _enrich_tags(
    user_id: str,
    *,
    db: AsyncSession,
    lf_client: LastfmClient,
    since: date | None = None,
) -> int:
    """Sync Last.fm tags for tracks listened to by ``user_id``.

    Returns the number of tracks processed.
    """

    if not lf_client.api_key:
        return 0

    q = (
        select(Track.track_id, Track.title, Artist.name)
        .join(Artist, Track.artist_id == Artist.artist_id)
        .join(Listen, Listen.track_id == Track.track_id)
        .where(Listen.user_id == user_id)
    )
    if since:
        q = q.where(Listen.played_at >= datetime.combine(since, datetime.min.time()))
    rows = (await db.execute(q)).all()

    updated = 0
    for tid, title, artist_name in rows:
        try:
            await lf_client.get_track_tags(db, tid, artist_name, title)
            updated += 1
        except Exception:  # pragma: no cover - network errors
            continue
    return updated


async def _enrich_ids(
    user_id: str,
    *,
    db: AsyncSession,
    mb_service: MusicBrainzService | None,
    since: date | None = None,
) -> int:
    """Attempt to resolve external identifiers for recently played tracks."""

    if mb_service is None:
        return 0

    q = (
        select(Track.track_id, Track.title, Artist.name)
        .join(Artist, Track.artist_id == Artist.artist_id)
        .join(Listen, Listen.track_id == Track.track_id)
        .where(Listen.user_id == user_id)
    )
    if since:
        q = q.where(Listen.played_at >= datetime.combine(since, datetime.min.time()))
    rows = (await db.execute(q)).all()

    enriched = 0
    for tid, title, artist_name in rows:
        try:
            await mb_service.recording_by_isrc(str(tid), title=title, artist=artist_name)
            enriched += 1
        except Exception:  # pragma: no cover - network errors
            continue
    return enriched


async def sync_user(
    user_id: str,
    *,
    db: AsyncSession,
    listen_service: ListenService,
    lb_client: ListenBrainzClient,
    lf_client: LastfmClient,
    sp_client: SpotifyClient,
    mb_service: MusicBrainzService | None,
    settings: Settings,
    since: date | None = None,
) -> dict[str, int]:
    """Synchronise listens and enrichment for ``user_id``."""

    result = SyncResult()
    result.ingested = await _fetch_listens(
        user_id,
        db=db,
        listen_service=listen_service,
        lb_client=lb_client,
        lf_client=lf_client,
        sp_client=sp_client,
        settings=settings,
        since=since,
    )
    result.tags_updated = await _enrich_tags(user_id, db=db, lf_client=lf_client, since=since)
    result.ids_enriched = await _enrich_ids(user_id, db=db, mb_service=mb_service, since=since)
    return result.to_dict()


__all__ = ["sync_user", "SyncResult"]
