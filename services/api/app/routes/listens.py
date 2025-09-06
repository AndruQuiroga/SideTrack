"""Endpoints for ingesting listen history."""

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.models import Artist, Listen, Release, Track

from ..db import get_db
from ..main import get_current_user, get_http_client
from ..utils import get_or_create, mb_sanitize

router = APIRouter()


class TrackIn(BaseModel):
    title: str
    artist_name: str
    release_title: str | None = None
    mbid: str | None = None
    duration: int | None = None
    path_local: str | None = None


class ListenIn(BaseModel):
    user_id: str
    played_at: datetime
    source: str | None = "listenbrainz"
    track: TrackIn


def _env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


# use shared utils: mb_sanitize, get_or_create


async def _lb_fetch_listens(
    client: httpx.AsyncClient,
    user: str,
    since: date | None,
    token: str | None = None,
    limit: int = 500,
) -> list[dict]:
    base = "https://api.listenbrainz.org/1/user"
    params: dict = {"count": min(limit, 1000)}
    if since:
        params["min_ts"] = int(datetime.combine(since, datetime.min.time(), tzinfo=UTC).timestamp())
    url = f"{base}/{user}/listens"
    r = await client.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("listens", [])


async def _ingest_lb_rows(db: AsyncSession, listens: list[dict], user_id: str | None = None) -> int:
    created = 0
    for item in listens:
        tm = item.get("track_metadata", {})
        artist_name = mb_sanitize(tm.get("artist_name") or tm.get("artist_name_mb")) or "Unknown"
        track_title = mb_sanitize(tm.get("track_name")) or "Unknown"
        release_title = mb_sanitize(tm.get("release_name"))
        recording_mbid = (tm.get("mbid_mapping") or {}).get("recording_mbid")
        played_at_ts = item.get("listened_at")
        if not played_at_ts:
            continue
        played_at = datetime.utcfromtimestamp(played_at_ts)
        uid = (user_id or item.get("user_name") or "lb").lower()

        artist = await get_or_create(db, Artist, name=artist_name)
        rel = None
        if release_title:
            rel = await get_or_create(db, Release, title=release_title, artist_id=artist.artist_id)
        track = await get_or_create(
            db,
            Track,
            mbid=recording_mbid,
            title=track_title,
            artist_id=artist.artist_id,
            release_id=rel.release_id if rel else None,
        )
        exists = (
            await db.execute(
                select(Listen).where(
                    and_(
                        Listen.user_id == uid,
                        Listen.track_id == track.track_id,
                        Listen.played_at == played_at,
                    )
                )
            )
        ).scalar_one_or_none()
        if not exists:
            db.add(
                Listen(
                    user_id=uid,
                    track_id=track.track_id,
                    played_at=played_at,
                    source="listenbrainz",
                )
            )
            created += 1
    await db.commit()
    return created


@router.post("/ingest/listens")
async def ingest_listens(
    since: date | None = Query(None),
    listens: list[ListenIn] | None = Body(None, description="List of listens to ingest"),
    source: str = Query("auto", description="auto|listenbrainz|body|sample"),
    db: AsyncSession = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_http_client),
    user_id: str = Depends(get_current_user),
):
    # 3 modes: body, ListenBrainz, or sample file
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
        created = await _ingest_lb_rows(db, rows, user_id)
        return {"detail": "ok", "ingested": created}

    if source in ("auto", "listenbrainz"):
        token = _env("LISTENBRAINZ_TOKEN")
        try:
            rows = await _lb_fetch_listens(client, user_id, since, token)
            created = await _ingest_lb_rows(db, rows, user_id)
            return {
                "detail": "ok",
                "ingested": created,
                "source": "listenbrainz",
            }
        except Exception as e:
            if source == "listenbrainz":
                raise HTTPException(status_code=502, detail=f"ListenBrainz error: {e}")
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
    created = await _ingest_lb_rows(db, rows, user_id)
    return {"detail": "ok", "ingested": created, "source": "sample"}
