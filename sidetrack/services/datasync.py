"""Utilities for synchronising listen history and enrichment.

This module orchestrates the full data synchronisation pipeline for a user:

1. Fetch listens from external providers (Spotify, Last.fm, ListenBrainz).
2. Normalise and store listens via :class:`~sidetrack.services.listens.ListenService`.
3. Enrich tracks with tags and external identifiers.

The main entry point is :func:`sync_user` which is designed for use by the
job runner or worker processes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.api.config import Settings
from sidetrack.services.listens import ListenService
from sidetrack.common.models import Artist, Listen, Track
from sidetrack.services.base_client import MusicServiceClient
from sidetrack.services.lastfm import LastfmClient
from sidetrack.services.listenbrainz import ListenBrainzClient
from sidetrack.services.musicbrainz import MusicBrainzService
from sidetrack.services.spotify import SpotifyClient
from sidetrack.services.maintenance import ingest_listens, OperationError


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
    clients: list[MusicServiceClient],
    settings: Settings,
    since: date | None = None,
) -> int:
    """Fetch and ingest recent listens for ``user_id``.

    The function mirrors the logic of the legacy ``/ingest/listens`` endpoint
    but is usable outside of the HTTP layer.
    """

    sp_client = next((c for c in clients if isinstance(c, SpotifyClient)), None)
    lf_client = next((c for c in clients if isinstance(c, LastfmClient)), None)
    lb_client = next((c for c in clients if isinstance(c, ListenBrainzClient)), None)

    try:
        result = await ingest_listens(
            db=db,
            listen_service=listen_service,
            user_id=user_id,
            settings=settings,
            since=since,
            source="auto",
            lb_client=lb_client,
            lf_client=lf_client,
            sp_client=sp_client,
            fallback_to_sample=False,
        )
    except OperationError:  # pragma: no cover - defensive
        return 0
    return result.ingested


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
    clients: list[MusicServiceClient],
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
        clients=clients,
        settings=settings,
        since=since,
    )
    lf_client = next((c for c in clients if isinstance(c, LastfmClient)), None)
    result.tags_updated = (
        await _enrich_tags(user_id, db=db, lf_client=lf_client, since=since)
        if lf_client
        else 0
    )
    result.ids_enriched = await _enrich_ids(
        user_id, db=db, mb_service=mb_service, since=since
    )
    return result.to_dict()


__all__ = ["sync_user", "SyncResult"]
