from sqlalchemy.ext.asyncio import AsyncSession

from services.common.models import Artist
from ..utils import get_or_create


class ArtistRepository:
    """Data access layer for :class:`Artist` objects."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, name: str, mbid: str | None = None) -> Artist:
        """Return existing artist or create a new one."""
        return await get_or_create(self.db, Artist, name=name, mbid=mbid)
