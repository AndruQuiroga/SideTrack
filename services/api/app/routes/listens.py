"""Endpoints for ingesting listen history."""

import json
from datetime import date, datetime
from pathlib import Path

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel

from ..config import Settings, get_settings
from ..main import get_current_user, get_http_client
from ..services.listen_service import ListenService, get_listen_service

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


@router.post("/ingest/listens")
async def ingest_listens(
    since: date | None = Query(None),
    listens: list[ListenIn] | None = Body(None, description="List of listens to ingest"),
    source: str = Query("auto", description="auto|listenbrainz|body|sample"),
    listen_service: ListenService = Depends(get_listen_service),
    client: httpx.AsyncClient = Depends(get_http_client),
    user_id: str = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
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
        created = await listen_service.ingest_lb_rows(rows, user_id)
        return {"detail": "ok", "ingested": created}

    if source in ("auto", "listenbrainz"):
        token = settings.listenbrainz_token
        try:
            rows = await listen_service.lb_fetch_listens(client, user_id, since, token)
            created = await listen_service.ingest_lb_rows(rows, user_id)
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
    created = await listen_service.ingest_lb_rows(rows, user_id)
    return {"detail": "ok", "ingested": created, "source": "sample"}
