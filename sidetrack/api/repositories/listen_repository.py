from datetime import datetime

from sqlalchemy import and_, insert, select, tuple_
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

    async def bulk_add(self, rows: list[dict]) -> int:
        """Insert many listens in a single batch.

        Existing listens for the same ``(user_id, track_id, played_at)`` are
        skipped via a single SELECT before the INSERT.
        """
        if not rows:
            return 0

        # Deduplicate input rows first
        unique: dict[tuple[str, int, datetime], dict] = {}
        for row in rows:
            key = (row["user_id"], row["track_id"], row["played_at"])
            unique.setdefault(key, row)
        rows = list(unique.values())

        keys = list(unique.keys())
        existing = await self.db.execute(
            select(Listen.user_id, Listen.track_id, Listen.played_at).where(
                tuple_(Listen.user_id, Listen.track_id, Listen.played_at).in_(keys)
            )
        )
        existing_keys = set(existing.all())
        to_insert = [row for key, row in zip(keys, rows) if key not in existing_keys]
        if not to_insert:
            return 0
        await self.db.execute(insert(Listen).values(to_insert))
        return len(to_insert)

    async def commit(self) -> None:
        await self.db.commit()
