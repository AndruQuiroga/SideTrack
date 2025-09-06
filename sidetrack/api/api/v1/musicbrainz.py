"""Endpoints for MusicBrainz-related ingestion."""

import time
from datetime import datetime

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import Artist, Release, Track

from ...db import get_db
from ...main import get_http_client
from ...schemas.musicbrainz import MusicbrainzIngestResponse
from ...utils import get_or_create, mb_sanitize

logger = structlog.get_logger(__name__)

router = APIRouter()


# use shared utils: mb_sanitize, get_or_create


_MB_LAST_CALL = 0.0


async def _mb_fetch_release(client: httpx.AsyncClient, mbid: str) -> dict:
    """Fetch release info from MusicBrainz with simple rate limiting."""
    global _MB_LAST_CALL
    wait = 1.0 - (time.time() - _MB_LAST_CALL)
    if wait > 0:
        time.sleep(wait)
    _MB_LAST_CALL = time.time()
    url = f"https://musicbrainz.org/ws/2/release/{mbid}"
    params = {"inc": "recordings+artists", "fmt": "json"}
    headers = {"User-Agent": "SideTrack/0.1 (+https://example.com)"}
    r = await client.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


@router.post("/ingest/musicbrainz", response_model=MusicbrainzIngestResponse)
async def ingest_musicbrainz(
    release_mbid: str = Query(..., description="MusicBrainz release MBID"),
    db: AsyncSession = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    try:
        data = await _mb_fetch_release(client, release_mbid)
    except httpx.HTTPError as exc:
        status = getattr(exc.response, "status_code", None)
        if status == 404:
            raise HTTPException(status_code=404, detail="release not found")
        logger.error("MusicBrainz HTTP error", error=str(exc))
        raise HTTPException(status_code=502, detail=f"MusicBrainz error: {exc}")
    except ValueError as exc:
        logger.error("MusicBrainz parse error", error=str(exc))
        raise HTTPException(status_code=502, detail=f"MusicBrainz error: {exc}")

    artist = None
    ac_list = data.get("artist-credit") or []
    if ac_list:
        art = (ac_list[0] or {}).get("artist", {})
        artist = await get_or_create(
            db,
            Artist,
            mbid=art.get("id"),
            defaults={"name": mb_sanitize(art.get("name") or art.get("sort-name") or "Unknown")},
        )

    rel_date = None
    if data.get("date"):
        try:
            rel_date = datetime.fromisoformat(data["date"]).date()
        except ValueError:
            rel_date = None
    label = None
    labels = data.get("label-info") or data.get("label-info-list") or []
    if labels:
        label = mb_sanitize((labels[0] or {}).get("label", {}).get("name"))

    release = await get_or_create(
        db,
        Release,
        mbid=data.get("id"),
        defaults={
            "title": mb_sanitize(data.get("title") or "Unknown"),
            "date": rel_date,
            "label": label,
            "artist_id": artist.artist_id if artist else None,
        },
    )

    created_tracks = 0
    for medium in data.get("media", []):
        for trk in medium.get("tracks", []):
            rec = trk.get("recording", {})
            track_mbid = rec.get("id")
            if not track_mbid:
                continue
            existing = (
                await db.execute(select(Track).filter_by(mbid=track_mbid))
            ).scalar_one_or_none()
            length = rec.get("length") or trk.get("length")
            duration = int(length / 1000) if length else None
            title = mb_sanitize(rec.get("title") or trk.get("title") or "Unknown")
            if existing is None:
                db.add(
                    Track(
                        mbid=track_mbid,
                        title=title,
                        artist_id=artist.artist_id if artist else None,
                        release_id=release.release_id,
                        duration=duration,
                    )
                )
                created_tracks += 1
            else:
                if artist and existing.artist_id is None:
                    existing.artist_id = artist.artist_id
                if existing.release_id is None:
                    existing.release_id = release.release_id
                if duration and existing.duration is None:
                    existing.duration = duration

    await db.commit()
    return MusicbrainzIngestResponse(
        detail="ok",
        artist_id=artist.artist_id if artist else None,
        release_id=release.release_id,
        tracks=created_tracks,
    )

