"""Recommendation candidate endpoints."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import UserSettings
from sidetrack.services.listenbrainz import ListenBrainzClient
from sidetrack.services.musicbrainz import MusicBrainzService
from sidetrack.services.recommendation import RecommendationService
from sidetrack.services.spotify import SpotifyUserClient
from sidetrack.services.lastfm import LastfmClient

from ...config import Settings
from ...config import get_settings as get_app_settings
from ...db import get_db
from ...main import _get_redis_connection, get_http_client
from ...security import get_current_user

router = APIRouter()


@router.get("/recs")
async def list_recs(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> dict:
    """Return recommendation candidates enriched with MusicBrainz data."""

    settings: Settings = get_app_settings()
    row = (
        await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="user settings not found")

    spotify_service: SpotifyUserClient | None = None
    lastfm_client: LastfmClient | None = None
    lastfm_user: str | None = None
    lb_client: ListenBrainzClient | None = None
    lb_user: str | None = None
    if settings.spotify_recs_enabled and row.spotify_access_token:
        spotify_service = SpotifyUserClient(
            client,
            access_token=row.spotify_access_token,
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            refresh_token=row.spotify_refresh_token,
        )
    elif settings.lastfm_similar_enabled and row.lastfm_user:
        lastfm_client = LastfmClient(client, settings.lastfm_api_key, None)
        lastfm_user = row.lastfm_user
    elif settings.lb_cf_enabled and row.listenbrainz_user:
        token = row.listenbrainz_token or settings.listenbrainz_token
        lb_client = ListenBrainzClient(
            client,
            user=row.listenbrainz_user,
            token=token,
        )
        lb_user = row.listenbrainz_user

    redis_conn = _get_redis_connection(settings)
    mb_service = MusicBrainzService(client, redis_conn=redis_conn, db=db)

    rec_service = RecommendationService(
        spotify=spotify_service,
        lastfm=lastfm_client,
        lastfm_user=lastfm_user,
        listenbrainz=lb_client,
        listenbrainz_user=lb_user,
        musicbrainz=mb_service,
    )

    result = await rec_service.generate_recommendations(include_ranked=False)
    return {"candidates": result.enriched}


@router.get("/recs/ranked")
async def ranked_recs(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> list[dict]:
    """Return ranked recommendation candidates."""

    settings: Settings = get_app_settings()
    row = (
        await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="user settings not found")

    spotify_service: SpotifyUserClient | None = None
    lastfm_client: LastfmClient | None = None
    lastfm_user: str | None = None
    lb_client: ListenBrainzClient | None = None
    lb_user: str | None = None
    if settings.spotify_recs_enabled and row.spotify_access_token:
        spotify_service = SpotifyUserClient(
            client,
            access_token=row.spotify_access_token,
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            refresh_token=row.spotify_refresh_token,
        )
    elif settings.lastfm_similar_enabled and row.lastfm_user:
        lastfm_client = LastfmClient(client, settings.lastfm_api_key, None)
        lastfm_user = row.lastfm_user
    elif settings.lb_cf_enabled and row.listenbrainz_user:
        token = row.listenbrainz_token or settings.listenbrainz_token
        lb_client = ListenBrainzClient(
            client,
            user=row.listenbrainz_user,
            token=token,
        )
        lb_user = row.listenbrainz_user

    redis_conn = _get_redis_connection(settings)
    mb_service = MusicBrainzService(client, redis_conn=redis_conn, db=db)
    rec_service = RecommendationService(
        spotify=spotify_service,
        lastfm=lastfm_client,
        lastfm_user=lastfm_user,
        listenbrainz=lb_client,
        listenbrainz_user=lb_user,
        musicbrainz=mb_service,
    )

    result = await rec_service.generate_recommendations(limit=limit)
    return [
        {
            k: item.get(k)
            for k in (
                "title",
                "artist",
                "spotify_id",
                "recording_mbid",
                "reasons",
                "final_score",
            )
            if item.get(k) is not None
        }
        for item in result.ranked
    ]
