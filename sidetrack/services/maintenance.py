"""High-level maintenance tasks for ingestion, enrichment, and aggregation."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.api import scoring as mood_scoring
from sidetrack.api.config import Settings
from sidetrack.api.constants import AXES, DEFAULT_METHOD
from sidetrack.common.models import (
    Artist,
    Listen,
    MoodAggWeek,
    MoodScore,
    Track,
    UserSettings,
)
from sidetrack.services.lastfm import LastfmClient
from sidetrack.services.listenbrainz import ListenBrainzClient
from sidetrack.services.listens import ListenService
from sidetrack.services.spotify import SpotifyClient

logger = logging.getLogger(__name__)


class OperationError(RuntimeError):
    """Generic error for maintenance operations with an HTTP status hint."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(slots=True)
class IngestResult:
    """Structured result for listen ingestion operations."""

    ingested: int
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"detail": "ok", "ingested": self.ingested}
        if self.source:
            payload["source"] = self.source
        return payload


async def ingest_listens(
    *,
    db: AsyncSession,
    listen_service: ListenService,
    user_id: str,
    settings: Settings,
    since: date | None = None,
    source: str = "auto",
    body_listens: list[dict[str, Any]] | None = None,
    lb_client: ListenBrainzClient | None = None,
    lf_client: LastfmClient | None = None,
    sp_client: SpotifyClient | None = None,
    fallback_to_sample: bool = True,
    sample_path: Path | None = None,
) -> IngestResult:
    """Ingest listens for ``user_id`` using the requested backend."""

    settings_row = (
        await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    ).scalar_one_or_none()

    sample_path = sample_path or Path("data/sample_listens.json")

    if source == "body" or body_listens is not None:
        if body_listens is None:
            raise OperationError("Body listens required for source=body", status_code=400)
        created = await listen_service.ingest_lb_rows(body_listens, user_id)
        return IngestResult(ingested=created, source="body")

    if source == "sample":
        return await _ingest_sample(listen_service, user_id, since, sample_path)

    if sp_client and source in {"auto", "spotify"}:
        token = settings_row.spotify_access_token if settings_row else None
        if token:
            since_dt = datetime.combine(since, datetime.min.time()) if since else None
            try:
                items = await sp_client.fetch_recently_played(token, after=since_dt)
            except httpx.HTTPError as exc:
                logger.error("Spotify fetch failed: %s", str(exc))
                if source == "spotify":
                    raise OperationError(
                        f"Spotify error: {exc}", status_code=502
                    ) from exc
            else:
                created = await listen_service.ingest_spotify_rows(items, user_id)
                return IngestResult(ingested=created, source="spotify")
        elif source == "spotify":
            raise OperationError("Spotify not connected", status_code=400)
    elif source == "spotify":
        raise OperationError("Spotify client unavailable", status_code=400)

    if lf_client and source in {"auto", "lastfm"}:
        if (
            settings_row
            and settings_row.lastfm_user
            and settings_row.lastfm_session_key
        ):
            since_dt = datetime.combine(since, datetime.min.time()) if since else None
            try:
                tracks = await lf_client.fetch_recent_tracks(
                    settings_row.lastfm_user, since_dt
                )
            except httpx.HTTPError as exc:
                logger.error("Last.fm fetch failed: %s", str(exc))
                if source == "lastfm":
                    raise OperationError(
                        f"Last.fm error: {exc}", status_code=502
                    ) from exc
            else:
                created = await listen_service.ingest_lastfm_rows(tracks, user_id)
                return IngestResult(ingested=created, source="lastfm")
        elif source == "lastfm":
            raise OperationError("Last.fm not connected", status_code=400)
    elif source == "lastfm":
        raise OperationError("Last.fm client unavailable", status_code=400)

    if lb_client and source in {"auto", "listenbrainz"}:
        token = settings.listenbrainz_token
        lb_user = user_id
        if settings_row:
            if settings_row.listenbrainz_token:
                token = settings_row.listenbrainz_token
            if settings_row.listenbrainz_user:
                lb_user = settings_row.listenbrainz_user
        try:
            rows = await lb_client.fetch_listens(lb_user, since, token)
        except httpx.HTTPError as exc:
            logger.error("ListenBrainz fetch failed: %s", str(exc))
            if source == "listenbrainz":
                raise OperationError(
                    f"ListenBrainz error: {exc}", status_code=502
                ) from exc
        else:
            created = await listen_service.ingest_lb_rows(rows, user_id)
            return IngestResult(ingested=created, source="listenbrainz")
    elif source == "listenbrainz":
        raise OperationError("ListenBrainz client unavailable", status_code=400)

    allow_sample = fallback_to_sample and source == "auto"
    if allow_sample:
        return await _ingest_sample(listen_service, user_id, since, sample_path)

    return IngestResult(ingested=0, source=None)


async def _ingest_sample(
    listen_service: ListenService,
    user_id: str,
    since: date | None,
    sample_path: Path,
) -> IngestResult:
    if not sample_path.exists():
        raise OperationError("No sample listens available", status_code=400)
    data = json.loads(sample_path.read_text())
    rows: list[dict[str, Any]] = []
    for item in data:
        played_at = datetime.fromisoformat(item["played_at"].replace("Z", "+00:00"))
        if since and played_at.date() < since:
            continue
        rows.append(
            {
                "track_metadata": {
                    "artist_name": item["track"].get("artist_name"),
                    "track_name": item["track"].get("title"),
                    "release_name": item["track"].get("release_title"),
                    "mbid_mapping": {"recording_mbid": item["track"].get("mbid")},
                },
                "listened_at": int(played_at.timestamp()),
                "user_name": item.get("user_id"),
            }
        )
    created = await listen_service.ingest_lb_rows(rows, user_id)
    return IngestResult(ingested=created, source="sample")


async def sync_lastfm_tags(
    *,
    db: AsyncSession,
    lf_client: LastfmClient,
    since: date | None = None,
) -> int:
    """Update cached Last.fm tags for tracks played since ``since``."""

    if not lf_client.api_key:
        raise OperationError("LASTFM_API_KEY not configured", status_code=400)

    stmt = select(Track.track_id, Track.title, Artist.name).join(
        Artist, Track.artist_id == Artist.artist_id
    )
    if since:
        stmt = stmt.join(Listen, Listen.track_id == Track.track_id).where(
            Listen.played_at >= datetime.combine(since, datetime.min.time())
        )
    rows = (await db.execute(stmt)).all()

    updated = 0
    for track_id, title, artist_name in rows:
        try:
            await lf_client.get_track_tags(db, track_id, artist_name, title)
            updated += 1
        except (RuntimeError, httpx.HTTPError) as exc:  # pragma: no cover - best effort
            logger.warning(
                "Tag sync failed track_id=%s error=%s", track_id, str(exc)
            )
    return updated


async def score_track(
    *,
    db: AsyncSession,
    track_id: int,
    method: str = DEFAULT_METHOD,
    version: str | None = None,
) -> dict[str, Any]:
    """Compute mood scores for ``track_id`` and persist them."""

    track = await db.get(Track, track_id)
    if not track:
        raise OperationError("track not found", status_code=404)

    try:
        scores = await mood_scoring.score_axes(db, track.track_id, method=method, version=version)
    except ValueError as exc:
        raise OperationError(str(exc), status_code=400) from exc

    method_name = mood_scoring.method_version(method, version)
    upserts = 0
    for axis, data in scores.items():
        value = data["value"]
        existing = (
            await db.execute(
                select(MoodScore).where(
                    and_(
                        MoodScore.track_id == track.track_id,
                        MoodScore.axis == axis,
                        MoodScore.method == method_name,
                    )
                )
            )
        ).scalar_one_or_none()
        if existing:
            existing.value = value
            existing.updated_at = datetime.utcnow()
        else:
            db.add(
                MoodScore(
                    track_id=track.track_id,
                    axis=axis,
                    method=method_name,
                    value=value,
                    updated_at=datetime.utcnow(),
                )
            )
            upserts += 1
    await db.commit()
    return {
        "detail": "scored",
        "track_id": track_id,
        "scores": scores,
        "upserts": upserts,
        "method": method_name,
    }


async def aggregate_weeks(
    *,
    db: AsyncSession,
    user_id: str,
    method: str = DEFAULT_METHOD,
) -> int:
    """Recompute weekly aggregates for ``user_id``."""

    listened_tracks = (
        await db.execute(
            select(Listen.track_id)
            .where(Listen.user_id == user_id)
            .distinct()
        )
    ).scalars().all()

    for track_id in listened_tracks:
        await score_track(db=db, track_id=track_id, method=method)

    method_name = mood_scoring.method_version(method, None)
    rows = (
        await db.execute(
            select(Listen.played_at, MoodScore.axis, MoodScore.value)
            .join(MoodScore, MoodScore.track_id == Listen.track_id)
            .where(
                and_(MoodScore.method == method_name, Listen.user_id == user_id)
            )
        )
    ).all()

    counts: dict[tuple[date, str], int] = {}
    sums: dict[tuple[date, str], float] = {}
    sums2: dict[tuple[date, str], float] = {}

    for played_at, axis, value in rows:
        week = _week_start(played_at)
        key = (week, axis)
        counts[key] = counts.get(key, 0) + 1
        sums[key] = sums.get(key, 0.0) + float(value)
        sums2[key] = sums2.get(key, 0.0) + float(value) * float(value)

    per_axis_weeks: dict[str, list[date]] = {ax: [] for ax in AXES}
    for week, axis in counts.keys():
        per_axis_weeks.setdefault(axis, []).append(week)
    for axis in per_axis_weeks.keys():
        per_axis_weeks[axis] = sorted(set(per_axis_weeks[axis]))

    await db.execute(delete(MoodAggWeek).where(MoodAggWeek.user_id == user_id))

    for (week, axis), count in counts.items():
        total = sums[(week, axis)]
        total_sq = sums2[(week, axis)]
        mean = total / count
        variance = max(0.0, total_sq / count - mean * mean)

        axis_weeks = per_axis_weeks[axis]
        index = axis_weeks.index(week)
        prev_mean = 0.0
        if index > 0:
            prev_week = axis_weeks[index - 1]
            prev_key = (prev_week, axis)
            if prev_key in counts:
                prev_mean = sums[prev_key] / counts[prev_key]
        momentum = mean - prev_mean

        db.add(
            MoodAggWeek(
                user_id=user_id,
                week=week,
                axis=axis,
                mean=mean,
                var=variance,
                momentum=momentum,
                sample_size=count,
            )
        )

    await db.commit()
    total = (await db.execute(select(func.count(MoodAggWeek.id)))).scalar() or 0
    return int(total)


def _week_start(dt: datetime) -> date:
    day = dt.date()
    return day - timedelta(days=day.weekday())


__all__ = [
    "IngestResult",
    "OperationError",
    "aggregate_weeks",
    "ingest_listens",
    "score_track",
    "sync_lastfm_tags",
]

