from datetime import datetime

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..repositories.artist_repository import ArtistRepository
from ..repositories.listen_repository import ListenRepository
from ..repositories.release_repository import ReleaseRepository
from ..repositories.track_repository import TrackRepository
from ..utils import mb_sanitize


class ListenService:
    """Service layer handling listen ingestion."""

    def __init__(
        self,
        artist_repo: ArtistRepository,
        release_repo: ReleaseRepository,
        track_repo: TrackRepository,
        listen_repo: ListenRepository,
    ):
        self.artists = artist_repo
        self.releases = release_repo
        self.tracks = track_repo
        self.listens = listen_repo

    async def ingest_lb_rows(self, listens: list[dict], user_id: str | None = None) -> int:
        """Ingest ListenBrainz-style listen rows into the database."""
        created = 0
        for item in listens:
            tm = item.get("track_metadata", {})
            artist_name = (
                mb_sanitize(tm.get("artist_name") or tm.get("artist_name_mb")) or "Unknown"
            )
            track_title = mb_sanitize(tm.get("track_name")) or "Unknown"
            release_title = mb_sanitize(tm.get("release_name"))
            recording_mbid = (tm.get("mbid_mapping") or {}).get("recording_mbid")
            played_at_ts = item.get("listened_at")
            if not played_at_ts:
                continue
            played_at = datetime.utcfromtimestamp(played_at_ts)
            uid = (user_id or item.get("user_name") or "lb").lower()

            artist = await self.artists.get_or_create(name=artist_name)
            rel = None
            if release_title:
                rel = await self.releases.get_or_create(
                    title=release_title, artist_id=artist.artist_id
                )
            track = await self.tracks.get_or_create(
                mbid=recording_mbid,
                title=track_title,
                artist_id=artist.artist_id,
                release_id=rel.release_id if rel else None,
            )
            if not await self.listens.exists(uid, track.track_id, played_at):
                await self.listens.add(uid, track.track_id, played_at, "listenbrainz")
                created += 1
        await self.listens.commit()
        return created


def get_listen_service(db: AsyncSession = Depends(get_db)) -> ListenService:
    """FastAPI dependency that provides a :class:`ListenService` instance."""
    artist_repo = ArtistRepository(db)
    release_repo = ReleaseRepository(db)
    track_repo = TrackRepository(db)
    listen_repo = ListenRepository(db)
    return ListenService(artist_repo, release_repo, track_repo, listen_repo)
