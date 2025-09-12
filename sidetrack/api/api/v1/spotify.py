"""Spotify integration endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import Feature, Track, UserSettings

from ....worker.jobs import fetch_spotify_features
from ...clients.spotify import SpotifyClient, get_spotify_client
from ...db import get_db
from ...repositories.artist_repository import ArtistRepository
from ...repositories.listen_repository import ListenRepository
from ...repositories.track_repository import TrackRepository
from ...security import get_current_user

router = APIRouter()


@router.post("/spotify/listens")
async def import_spotify_listens(
    sp_client: SpotifyClient = Depends(get_spotify_client),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Fetch and ingest the user's recent Spotify listens."""

    row = (
        await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    ).scalar_one_or_none()
    if not row or not row.spotify_access_token:
        raise HTTPException(status_code=400, detail="Spotify not connected")

    items = await sp_client.fetch_recently_played(row.spotify_access_token)

    artist_repo = ArtistRepository(db)
    track_repo = TrackRepository(db)
    listen_repo = ListenRepository(db)

    created = 0
    for item in items:
        track_data = item.get("track") or {}
        spotify_id = track_data.get("id")
        if not spotify_id:
            continue

        artist_name = (track_data.get("artists") or [{}])[0].get("name") or "Unknown"
        title = track_data.get("name") or "Unknown"
        played_at = datetime.fromisoformat(item["played_at"].replace("Z", "+00:00"))

        artist = await artist_repo.get_or_create(artist_name)
        track = await track_repo.get_or_create_spotify(spotify_id, title, artist.artist_id)

        if not await listen_repo.exists(user_id, track.track_id, played_at):
            await listen_repo.add(user_id, track.track_id, played_at, "spotify")
            created += 1

    await listen_repo.commit()
    return {"detail": "ok", "ingested": created}


@router.post("/spotify/features/backfill")
async def spotify_features_backfill(
    sp_client: SpotifyClient = Depends(get_spotify_client),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Backfill Spotify features for all tracks missing them."""

    row = (
        await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    ).scalar_one_or_none()
    if not row or not row.spotify_access_token:
        raise HTTPException(status_code=400, detail="Spotify not connected")

    stmt = (
        select(Track)
        .outerjoin(Feature, Feature.track_id == Track.track_id)
        .where(Track.spotify_id.is_not(None))
        .where(Feature.track_id.is_(None))
    )
    tracks = (await db.execute(stmt)).scalars().all()
    count = 0
    for track in tracks:
        try:
            await fetch_spotify_features(track.track_id, row.spotify_access_token, sp_client)
            count += 1
        except Exception:
            continue
    return {"detail": "ok", "backfilled": count}


@router.post("/spotify/features/{track_id}")
async def spotify_track_features(
    track_id: int,
    sp_client: SpotifyClient = Depends(get_spotify_client),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Backfill or retrieve Spotify audio features for a track."""

    row = (
        await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    ).scalar_one_or_none()
    if not row or not row.spotify_access_token:
        raise HTTPException(status_code=400, detail="Spotify not connected")

    track = await db.get(Track, track_id)
    if not track or not track.spotify_id:
        raise HTTPException(status_code=404, detail="Track not found")

    feature = (
        await db.execute(select(Feature).where(Feature.track_id == track_id))
    ).scalar_one_or_none()
    if feature:
        return {"detail": "ok", "status": "exists", "feature_id": feature.id}

    fid = await fetch_spotify_features(track_id, row.spotify_access_token, sp_client)
    return {"detail": "ok", "status": "created", "feature_id": fid}


@router.get("/spotify/now")
async def spotify_now_playing(
    sp_client: SpotifyClient = Depends(get_spotify_client),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    row = (
        await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    ).scalar_one_or_none()
    if not row or not row.spotify_access_token:
        return {"playing": False}
    try:
        data = await sp_client.get_currently_playing(row.spotify_access_token)
    except Exception:
        return {"playing": False}
    if not data or not data.get("item"):
        return {"playing": False}
    item = data.get("item") or {}
    title = item.get("name") or ""
    artists = ", ".join([a.get("name") for a in (item.get("artists") or []) if a.get("name")])
    return {"playing": True, "title": title, "artist": artists}
