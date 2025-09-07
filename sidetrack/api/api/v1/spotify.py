"""Spotify integration endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import UserSettings

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
        track = await track_repo.get_or_create_spotify(
            spotify_id, title, artist.artist_id
        )

        if not await listen_repo.exists(user_id, track.track_id, played_at):
            await listen_repo.add(user_id, track.track_id, played_at, "spotify")
            created += 1

    await listen_repo.commit()
    return {"detail": "ok", "ingested": created}

