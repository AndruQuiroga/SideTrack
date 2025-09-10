"""Recommendation candidate endpoints."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import UserSettings
from sidetrack.services.candidates import generate_candidates
from sidetrack.services.lastfm import LastfmService
from sidetrack.services.mb_map import recording_by_isrc
from sidetrack.services.ranker import profile_from_spotify, rank
from sidetrack.services.spotify import SpotifyService

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

    spotify_service: SpotifyService | None = None
    lastfm_service: LastfmService | None = None
    lastfm_user: str | None = None
    if row.spotify_access_token:
        spotify_service = SpotifyService(client, access_token=row.spotify_access_token)
    elif row.lastfm_user:
        lastfm_service = LastfmService(client, settings.lastfm_api_key)
        lastfm_user = row.lastfm_user

    candidates = await generate_candidates(
        spotify=spotify_service, lastfm=lastfm_service, lastfm_user=lastfm_user
    )

    redis_conn = _get_redis_connection(settings)

    enriched: list[dict] = []
    for cand in candidates:
        item = {
            "artist": cand.get("artist"),
            "title": cand.get("title"),
            "source": cand.get("source"),
            "score_cf": cand.get("score_cf"),
        }
        isrc = cand.get("isrc")
        if isrc:
            rec_mbid, art_mbid, year, label, tags = await recording_by_isrc(
                isrc, client=client, redis_conn=redis_conn
            )
            item.update(
                {
                    "recording_mbid": rec_mbid,
                    "artist_mbid": art_mbid,
                    "release_year": year,
                    "label": label,
                    "tags": tags,
                }
            )
        else:
            item["spotify_id"] = cand.get("spotify_id")
        enriched.append(item)

    return {"candidates": enriched}


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

    spotify_service: SpotifyService | None = None
    lastfm_service: LastfmService | None = None
    lastfm_user: str | None = None
    if row.spotify_access_token:
        spotify_service = SpotifyService(client, access_token=row.spotify_access_token)
    elif row.lastfm_user:
        lastfm_service = LastfmService(client, settings.lastfm_api_key)
        lastfm_user = row.lastfm_user

    candidates = await generate_candidates(
        spotify=spotify_service, lastfm=lastfm_service, lastfm_user=lastfm_user
    )

    redis_conn = _get_redis_connection(settings)

    enriched: list[dict] = []
    spotify_ids: list[str] = []
    for cand in candidates:
        item: dict[str, Any] = {
            "artist": cand.get("artist"),
            "title": cand.get("title"),
            "score_cf": cand.get("score_cf"),
        }
        isrc = cand.get("isrc")
        if isrc:
            rec_mbid, art_mbid, year, label, _tags = await recording_by_isrc(
                isrc, client=client, redis_conn=redis_conn
            )
            item.update(
                {
                    "recording_mbid": rec_mbid,
                    "artist_mbid": art_mbid,
                    "label": label,
                }
            )
        else:
            sid = cand.get("spotify_id")
            if sid:
                item["spotify_id"] = sid
                spotify_ids.append(sid)
        enriched.append(item)

    user_profile: dict[str, float] = {}
    if spotify_service:
        user_profile = await profile_from_spotify(spotify_service)
        if spotify_ids:
            feats = await spotify_service.get_audio_features(spotify_ids)
            feat_map = {f.get("id"): f for f in feats}
            for item in enriched:
                sid = item.get("spotify_id")
                if sid and sid in feat_map:
                    item["audio_features"] = feat_map[sid]

    ranked = rank(enriched, user_profile)
    out: list[dict] = []
    for item in ranked[:limit]:
        out.append(
            {
                k: item.get(k)
                for k in ("title", "artist", "spotify_id", "recording_mbid", "reasons", "final_score")
                if item.get(k) is not None
            }
        )
    return out
