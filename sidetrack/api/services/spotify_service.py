from datetime import datetime

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..repositories.artist_repository import ArtistRepository
from ..repositories.listen_repository import ListenRepository
from ..repositories.track_repository import TrackRepository


class SpotifyService:
    """Service for importing Spotify listen history."""

    def __init__(
        self,
        artist_repo: ArtistRepository,
        track_repo: TrackRepository,
        listen_repo: ListenRepository,
    ) -> None:
        self.artists = artist_repo
        self.tracks = track_repo
        self.listens = listen_repo

    async def ingest_recently_played(
        self, items: list[dict], user_id: str
    ) -> int:
        """Ingest Spotify recently played items."""
        created = 0
        for item in items:
            track = item.get("track") or {}
            spotify_id = track.get("id")
            if not spotify_id:
                continue
            artist_name = (
                (track.get("artists") or [{}])[0].get("name") or "Unknown"
            )
            track_title = track.get("name") or "Unknown"
            duration_ms = track.get("duration_ms")
            played_at_str = item.get("played_at")
            if not played_at_str:
                continue
            played_at = datetime.fromisoformat(played_at_str.replace("Z", "+00:00"))
            artist = await self.artists.get_or_create(name=artist_name)
            db_track = await self.tracks.get_or_create_spotify(
                spotify_id=spotify_id,
                title=track_title,
                artist_id=artist.artist_id,
                duration=int(duration_ms / 1000) if duration_ms else None,
            )
            if not await self.listens.exists(user_id, db_track.track_id, played_at):
                await self.listens.add(user_id, db_track.track_id, played_at, "spotify")
                created += 1
        await self.listens.commit()
        return created


def get_spotify_service(db: AsyncSession = Depends(get_db)) -> SpotifyService:
    artist_repo = ArtistRepository(db)
    track_repo = TrackRepository(db)
    listen_repo = ListenRepository(db)
    return SpotifyService(artist_repo, track_repo, listen_repo)
