from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import Track

from ..utils import get_or_create


class TrackRepository:
    """Data access layer for :class:`Track` objects."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(
        self,
        mbid: str | None,
        title: str,
        artist_id: int,
        release_id: int | None = None,
        duration: int | None = None,
        path_local: str | None = None,
    ) -> Track:
        return await get_or_create(
            self.db,
            Track,
            mbid=mbid,
            title=title,
            artist_id=artist_id,
            release_id=release_id,
            duration=duration,
            path_local=path_local,
        )

    async def get_or_create_spotify(
        self,
        spotify_id: str,
        title: str,
        artist_id: int,
        release_id: int | None = None,
        duration: int | None = None,
    ) -> Track:
        defaults = {
            "title": title,
            "artist_id": artist_id,
            "release_id": release_id,
            "duration": duration,
        }
        return await get_or_create(
            self.db,
            Track,
            defaults=defaults,
            spotify_id=spotify_id,
        )
