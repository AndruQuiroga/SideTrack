"""Utilities for synchronising listen history and enrichment.

This module orchestrates the full data synchronisation pipeline for a user:

1. Fetch listens from external providers (Spotify, Last.fm, ListenBrainz).
2. Normalise and store listens via :class:`~sidetrack.services.listens.ListenService`.
3. Enrich tracks with tags and external identifiers.

The main entry point is :func:`sync_user` which is designed for use by the
job runner or worker processes.
"""

from __future__ import annotations

import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.api.config import Settings
from sidetrack.services.listens import ListenService
from sidetrack.analytics.tags import canonicalize_tag, label_rollups
from sidetrack.common.models import Artist, Listen, Track, MBLabel, Release
from sidetrack.enrichment.fusion import persist_mb_label, persist_mb_tags
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


@dataclass
class IdEnrichmentResult:
    """Summary of MusicBrainz identifier enrichment."""

    processed: int = 0
    enriched: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "processed": self.processed,
            "enriched": self.enriched,
            "errors": self.errors,
        }


_ISRC_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$")


def _normalise_isrc(value: str | None) -> str | None:
    if not value:
        return None
    candidate = str(value).strip().upper()
    if _ISRC_RE.match(candidate):
        return candidate
    return None


def _normalise_uuid(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


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
) -> IdEnrichmentResult:
    """Resolve external identifiers and label metadata for the user's tracks."""

    result = IdEnrichmentResult()
    if mb_service is None:
        return result

    q = (
        select(
            Track.track_id.label("track_id"),
            Track.title.label("title"),
            Artist.artist_id.label("artist_id"),
            Artist.name.label("artist_name"),
            Track.isrc.label("track_isrc"),
            Track.mbid.label("track_mbid"),
            Artist.mbid.label("artist_mbid"),
            Track.release_id.label("release_id"),
            Release.mbid.label("release_mbid"),
            MBLabel.id.label("label_id"),
        )
        .join(Artist, Track.artist_id == Artist.artist_id)
        .join(Listen, Listen.track_id == Track.track_id)
        .outerjoin(Release, Track.release_id == Release.release_id)
        .outerjoin(MBLabel, MBLabel.track_id == Track.track_id)
        .where(Listen.user_id == user_id)
    )
    if since:
        q = q.where(Listen.played_at >= datetime.combine(since, datetime.min.time()))
    q = q.where(
        or_(
            Track.mbid.is_(None),
            Artist.mbid.is_(None),
            and_(Track.release_id.is_not(None), Release.mbid.is_(None)),
            MBLabel.id.is_(None),
        )
    ).distinct()

    rows = (await db.execute(q)).mappings().all()
    result.processed = len(rows)

    for row in rows:
        track_id = row["track_id"]
        title = row["title"]
        artist_name = row["artist_name"]

        track = await db.get(Track, track_id)
        if track is None:  # pragma: no cover - defensive
            continue

        existing_track_mbid = _normalise_uuid(row["track_mbid"])
        existing_artist_mbid = _normalise_uuid(row["artist_mbid"])
        existing_release_mbid = _normalise_uuid(row["release_mbid"])
        isrc = _normalise_isrc(row["track_isrc"])

        if not (isrc or existing_track_mbid or (title and artist_name)):
            result.errors.append({"track_id": str(track_id), "error": "insufficient metadata"})
            continue

        try:
            data = await mb_service.recording_by_isrc(
                isrc,
                title=title,
                artist=artist_name,
                recording_mbid=existing_track_mbid,
            )
        except Exception as exc:  # pragma: no cover - best effort
            result.errors.append({"track_id": str(track_id), "error": str(exc)})
            continue

        updated = False

        track_mbid = _normalise_uuid(data.get("recording_mbid"))
        if track_mbid and track_mbid != existing_track_mbid:
            track.mbid = track_mbid
            updated = True

        data_isrc = _normalise_isrc(data.get("isrc"))
        if data_isrc and data_isrc != _normalise_isrc(track.isrc):
            track.isrc = data_isrc
            updated = True

        artist_mbid = _normalise_uuid(data.get("artist_mbid"))
        if artist_mbid and row["artist_id"] is not None and artist_mbid != existing_artist_mbid:
            artist = await db.get(Artist, row["artist_id"])
            if artist:
                artist.mbid = artist_mbid
                updated = True

        release_group = _normalise_uuid(data.get("release_group_mbid"))
        if (
            release_group
            and row["release_id"] is not None
            and release_group != existing_release_mbid
        ):
            release = await db.get(Release, row["release_id"])
            if release:
                release.mbid = release_group
                updated = True

        label_updated = False
        tags_updated = False
        if row["label_id"] is None:
            label_name = data.get("label")
            year = data.get("year")
            if label_name or year is not None:
                labels_payload = (
                    [{"name": label_name, "country": None}] if label_name else []
                )
                rollup = label_rollups(labels_payload, year)
                await persist_mb_label(db, track_id, rollup)
                label_updated = True
                updated = True

        tags = data.get("tags") or []
        if tags:
            counter: Counter[str] = Counter()
            for tag in tags:
                key = canonicalize_tag(str(tag))
                if key:
                    counter[key] += 1
            if counter:
                await persist_mb_tags(
                    db,
                    track_id,
                    {tag: float(score) for tag, score in counter.items()},
                )
                tags_updated = True
                updated = True

        if updated and not (label_updated or tags_updated):
            await db.commit()

        if updated:
            result.enriched += 1

    return result


async def enrich_ids(
    user_id: str,
    *,
    db: AsyncSession,
    mb_service: MusicBrainzService | None,
    since: date | None = None,
) -> IdEnrichmentResult:
    """Public helper that returns MusicBrainz enrichment summary."""

    return await _enrich_ids(user_id, db=db, mb_service=mb_service, since=since)


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
    ids_result = await _enrich_ids(user_id, db=db, mb_service=mb_service, since=since)
    result.ids_enriched = ids_result.enriched
    return result.to_dict()


__all__ = ["sync_user", "SyncResult", "enrich_ids", "IdEnrichmentResult"]
