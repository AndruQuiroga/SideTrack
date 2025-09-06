from sqlalchemy.ext.asyncio import AsyncSession

from services.common.models import Release
from ..utils import get_or_create


class ReleaseRepository:
    """Data access layer for :class:`Release` objects."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(
        self,
        title: str,
        artist_id: int,
        mbid: str | None = None,
        date=None,
        label=None,
    ) -> Release:
        return await get_or_create(
            self.db,
            Release,
            title=title,
            artist_id=artist_id,
            mbid=mbid,
            date=date,
            label=label,
        )
