from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import Listen


class ListenRepository:
    """Data access layer for :class:`Listen` objects."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def exists(self, user_id: str, track_id: int, played_at: datetime) -> bool:
        """Check if a listen already exists for the given identifiers."""
        res = await self.db.execute(
            select(Listen).where(
                and_(
                    Listen.user_id == user_id,
                    Listen.track_id == track_id,
                    Listen.played_at == played_at,
                )
            )
        )
        return res.scalar_one_or_none() is not None

    async def add(self, user_id: str, track_id: int, played_at: datetime, source: str) -> None:
        """Add a new listen to the session."""
        self.db.add(
            Listen(
                user_id=user_id,
                track_id=track_id,
                played_at=played_at,
                source=source,
            )
        )

    async def commit(self) -> None:
        await self.db.commit()
