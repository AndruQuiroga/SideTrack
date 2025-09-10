"""Utilities for generating and retrieving listening insights."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import JSON, DateTime, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from sidetrack.common.models import Base, Listen


class InsightEvent(Base):
    __tablename__ = "insight_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    type: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSON)
    severity: Mapped[int] = mapped_column(Integer, default=0)


async def compute_weekly_insights(db: AsyncSession, user_id: str) -> Sequence[InsightEvent]:
    """Compute simple weekly insights for a user and persist them.

    This implementation is intentionally lightweight; it currently records a
    single insight with the number of listens in the past week. More advanced
    analytics (changepoints, genre deltas, discovery rate, etc.) can be added
    later.
    """

    now = datetime.now(UTC)
    since = now - timedelta(days=7)

    total = (
        await db.execute(
            select(func.count())
            .select_from(Listen)
            .where(Listen.user_id == user_id, Listen.played_at >= since)
        )
    ).scalar()

    events: list[InsightEvent] = []
    if total:
        evt = InsightEvent(
            user_id=user_id,
            ts=now,
            type="weekly_listens",
            summary=f"{int(total)} listens this week",
            details={"count": int(total)},
            severity=0,
        )
        db.add(evt)
        await db.commit()
        await db.refresh(evt)
        events.append(evt)
    return events


async def get_insights(db: AsyncSession, user_id: str, since: datetime) -> Sequence[InsightEvent]:
    """Return insight events for ``user_id`` since ``since``."""

    rows = (
        await db.execute(
            select(InsightEvent)
            .where(InsightEvent.user_id == user_id, InsightEvent.ts >= since)
            .order_by(InsightEvent.ts.desc())
        )
    ).scalars()
    return list(rows)
