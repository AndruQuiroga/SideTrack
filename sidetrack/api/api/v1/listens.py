"""Endpoints for ingesting listen history."""

from datetime import date
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import Artist, Listen, Track

from sidetrack.services.lastfm import LastfmClient, get_lastfm_client
from ....services.spotify import SpotifyClient, get_spotify_client
from sidetrack.services.listenbrainz import ListenBrainzClient, get_listenbrainz_client
from ...config import Settings, get_settings
from ...db import get_db
from ...schemas.listens import IngestResponse, ListenIn, RecentListensResponse
from ...security import get_current_user
from sidetrack.services.listens import ListenService, get_listen_service
from sidetrack.services.maintenance import ingest_listens as ingest_task, OperationError

router = APIRouter()


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
    """Ingest listens from a variety of external services."""

    source_override = source
    body_rows = None
    if listens is not None:
        body_rows = [
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
        source_override = "body"

    try:
        result = await ingest_task(
            db=db,
            listen_service=listen_service,
            user_id=user_id,
            settings=settings,
            since=since,
            source=source_override,
            body_listens=body_rows,
            lb_client=lb_client,
            lf_client=lf_client,
            sp_client=sp_client,
        )
    except OperationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    payload = result.to_dict()
    if source_override == "body":
        payload.pop("source", None)
    return IngestResponse(**payload)
