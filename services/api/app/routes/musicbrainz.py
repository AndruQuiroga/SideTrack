"""Endpoints for MusicBrainz-related ingestion."""

from datetime import datetime
from typing import Dict, Optional

import requests
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Artist, Release, Track
from ..main import HTTP_SESSION


router = APIRouter()


def _mb_sanitize(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return s.strip().replace("\u0000", "")


def _get_or_create(db: Session, model, defaults: Dict | None = None, **kwargs):
    inst = db.execute(select(model).filter_by(**kwargs)).scalar_one_or_none()
    if inst:
        return inst
    params = {**kwargs}
    if defaults:
        params.update(defaults)
    inst = model(**params)
    db.add(inst)
    db.flush()
    return inst


_MB_LAST_CALL = 0.0


def _mb_fetch_release(mbid: str) -> dict:
    """Fetch release info from MusicBrainz with simple rate limiting."""
    global _MB_LAST_CALL
    wait = 1.0 - (time.time() - _MB_LAST_CALL)
    if wait > 0:
        time.sleep(wait)
    _MB_LAST_CALL = time.time()
    url = f"https://musicbrainz.org/ws/2/release/{mbid}"
    params = {"inc": "recordings+artists", "fmt": "json"}
    headers = {"User-Agent": "SideTrack/0.1 (+https://example.com)"}
    r = HTTP_SESSION.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


@router.post("/ingest/musicbrainz")
def ingest_musicbrainz(
    release_mbid: str = Query(..., description="MusicBrainz release MBID"),
    db: Session = Depends(get_db),
):
    try:
        data = _mb_fetch_release(release_mbid)
    except requests.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        if status == 404:
            raise HTTPException(status_code=404, detail="release not found")
        raise HTTPException(status_code=502, detail=f"MusicBrainz error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"MusicBrainz error: {e}")

    artist = None
    ac_list = data.get("artist-credit") or []
    if ac_list:
        art = (ac_list[0] or {}).get("artist", {})
        artist = _get_or_create(
            db,
            Artist,
            mbid=art.get("id"),
            defaults={
                "name": _mb_sanitize(
                    art.get("name") or art.get("sort-name") or "Unknown"
                )
            },
        )

    rel_date = None
    if data.get("date"):
        try:
            rel_date = datetime.fromisoformat(data["date"]).date()
        except Exception:
            rel_date = None
    label = None
    labels = data.get("label-info") or data.get("label-info-list") or []
    if labels:
        label = _mb_sanitize((labels[0] or {}).get("label", {}).get("name"))

    release = _get_or_create(
        db,
        Release,
        mbid=data.get("id"),
        defaults={
            "title": _mb_sanitize(data.get("title") or "Unknown"),
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
            existing = db.execute(select(Track).filter_by(mbid=track_mbid)).scalar_one_or_none()
            length = rec.get("length") or trk.get("length")
            duration = int(length / 1000) if length else None
            title = _mb_sanitize(rec.get("title") or trk.get("title") or "Unknown")
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

    db.commit()
    return {
        "detail": "ok",
        "artist_id": artist.artist_id if artist else None,
        "release_id": release.release_id,
        "tracks": created_tracks,
    }

