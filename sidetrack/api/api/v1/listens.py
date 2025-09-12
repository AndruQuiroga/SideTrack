"""Endpoints for ingesting listen history."""

import json
import logging
from datetime import date, datetime
from pathlib import Path

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import Artist, Listen, Track, UserSettings

from ...clients.lastfm import LastfmClient, get_lastfm_client
from ...clients.listenbrainz import ListenBrainzClient, get_listenbrainz_client
from ...clients.spotify import SpotifyClient, get_spotify_client
from ...config import Settings, get_settings
from ...db import get_db
from ...schemas.listens import IngestResponse, ListenIn, RecentListensResponse
from ...security import get_current_user
from ...services.listen_service import ListenService, get_listen_service

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/listens/recent", response_model=RecentListensResponse)
async def recent_listens(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(Listen.played_at, Track.track_id, Track.title, Artist.name)
            .join(Track, Track.track_id == Listen.track_id)
            .join(Artist, Track.artist_id == Artist.artist_id, isouter=True)
            .where(Listen.user_id == user_id)
            .order_by(Listen.played_at.desc())
            .limit(limit)
        )
    ).all()
    listens = [
        {
            "track_id": tid,
            "title": title,
            "artist": artist,
            "played_at": played_at,
        }
        for played_at, tid, title, artist in rows
    ]
    return {"listens": listens}


@router.post("/ingest/listens", response_model=IngestResponse)
async def ingest_listens(
    since: date | None = Query(None),
    listens: list[ListenIn] | None = Body(None, description="List of listens to ingest"),
    source: str = Query("auto", description="auto|spotify|lastfm|listenbrainz|body|sample"),
    listen_service: ListenService = Depends(get_listen_service),
    lb_client: ListenBrainzClient = Depends(get_listenbrainz_client),
    lf_client: LastfmClient = Depends(get_lastfm_client),
    sp_client: SpotifyClient = Depends(get_spotify_client),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Ingest listens from a variety of external services.

    ``source`` determines which backend to use.  In ``auto`` mode the function
    attempts Spotify, then Last.fm, and finally ListenBrainz before falling
    back to bundled sample data.
    """
    # multiple modes: body, Spotify, Last.fm, ListenBrainz, or sample file
    if source == "body" and listens is None:
        raise HTTPException(status_code=400, detail="Body listens required for source=body")

    if listens is not None:
        # Ingest provided body
        rows = [
            {
                "track_metadata": {
                    "artist_name": ls.track.artist_name,
                    "track_name": ls.track.title,
                    "release_name": ls.track.release_title,
                    "mbid_mapping": {"recording_mbid": ls.track.mbid},
                },
                "listened_at": int(ls.played_at.timestamp()),
                "user_name": ls.user_id,
            }
            for ls in listens
            if not since or ls.played_at.date() >= since
        ]
        created = await listen_service.ingest_lb_rows(rows, user_id)
        return IngestResponse(detail="ok", ingested=created)

    # Load user settings for external tokens
    settings_row = (
        await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    ).scalar_one_or_none()

    # Try Spotify first
    if source in ("auto", "spotify"):
        token = settings_row.spotify_access_token if settings_row else None
        if token:
            try:
                since_dt = datetime.combine(since, datetime.min.time()) if since else None
                items = await sp_client.fetch_recently_played(token, after=since_dt)
                created = await listen_service.ingest_spotify_rows(items, user_id)
                return IngestResponse(detail="ok", ingested=created, source="spotify")
            except httpx.HTTPError as exc:
                logger.error("Spotify fetch failed: %s", str(exc))
                if source == "spotify":
                    raise HTTPException(status_code=502, detail=f"Spotify error: {exc}")
        elif source == "spotify":
            raise HTTPException(status_code=400, detail="Spotify not connected")

    # Next try Last.fm
    if source in ("auto", "lastfm"):
        if settings_row and settings_row.lastfm_user and settings_row.lastfm_session_key:
            try:
                since_dt = datetime.combine(since, datetime.min.time()) if since else None
                tracks = await lf_client.fetch_recent_tracks(settings_row.lastfm_user, since_dt)
                created = await listen_service.ingest_lastfm_rows(tracks, user_id)
                return IngestResponse(detail="ok", ingested=created, source="lastfm")
            except httpx.HTTPError as exc:
                logger.error("Last.fm fetch failed: %s", str(exc))
                if source == "lastfm":
                    raise HTTPException(status_code=502, detail=f"Last.fm error: {exc}")
        elif source == "lastfm":
            raise HTTPException(status_code=400, detail="Last.fm not connected")

    # Finally fall back to ListenBrainz
    if source in ("auto", "listenbrainz"):
        token = settings_row.listenbrainz_token if settings_row else settings.listenbrainz_token
        lb_user = settings_row.listenbrainz_user if settings_row else user_id
        try:
            rows = await lb_client.fetch_listens(lb_user, since, token)
            created = await listen_service.ingest_lb_rows(rows, user_id)
            return IngestResponse(detail="ok", ingested=created, source="listenbrainz")
        except httpx.HTTPError as exc:
            logger.error("ListenBrainz fetch failed: %s", str(exc))
            if source == "listenbrainz":
                raise HTTPException(status_code=502, detail=f"ListenBrainz error: {exc}")
            # fall through to sample

    sample_path = Path("data/sample_listens.json")
    if not sample_path.exists():
        raise HTTPException(status_code=400, detail="No sample listens available")
    data = json.loads(sample_path.read_text())
    rows = []
    for x in data:
        dt = datetime.fromisoformat(x["played_at"].replace("Z", "+00:00"))
        if since and dt.date() < since:
            continue
        rows.append(
            {
                "track_metadata": {
                    "artist_name": x["track"]["artist_name"],
                    "track_name": x["track"]["title"],
                    "release_name": x["track"].get("release_title"),
                    "mbid_mapping": {"recording_mbid": x["track"].get("mbid")},
                },
                "listened_at": int(dt.timestamp()),
                "user_name": x["user_id"],
            }
        )
    created = await listen_service.ingest_lb_rows(rows, user_id)
    return IngestResponse(detail="ok", ingested=created, source="sample")
