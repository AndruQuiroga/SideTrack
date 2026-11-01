"""Dated timezone periods and the time-aware zone lookup."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import User, UserTimezonePeriod


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise ValueError("invalid_timezone") from exc


def _start(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("naive_datetime")
    return value.astimezone(UTC)


def list_timezone_periods(db: Session, user_id: UUID) -> list[UserTimezonePeriod]:
    """A user's periods, earliest first."""

    return list(
        db.scalars(
            select(UserTimezonePeriod)
            .where(UserTimezonePeriod.user_id == user_id)
            .order_by(UserTimezonePeriod.effective_from)
        )
    )


def add_timezone_period(
    db: Session, user_id: UUID, effective_from: datetime, timezone: str
) -> UserTimezonePeriod:
    """Add a period starting at `effective_from`. The caller owns the transaction."""

    _zone(timezone)
    start = _start(effective_from)
    if db.get(User, user_id) is None:
        raise ValueError("user_unavailable")
    if db.get(UserTimezonePeriod, (user_id, start)) is not None:
        raise ValueError("duplicate_period")
    period = UserTimezonePeriod(
        user_id=user_id, effective_from=start, timezone=timezone, created_at=datetime.now(UTC)
    )
    db.add(period)
    db.flush()
    return period


def remove_timezone_period(db: Session, user_id: UUID, effective_from: datetime) -> None:
    """Remove the period that starts at `effective_from`. The caller owns the transaction."""

    period = db.get(UserTimezonePeriod, (user_id, _start(effective_from)))
    if period is None:
        raise ValueError("period_not_found")
    db.delete(period)
    db.flush()


def timezone_resolver(db: Session, user_id: UUID) -> Callable[[datetime], ZoneInfo | None]:
    """A function from a moment to the user's zone then, from one periods query.

    The period containing the moment wins. Before the first period, or with none, the
    user's `timezone` applies, and with neither the result is None. Nothing guesses a zone.
    """

    user = db.get(User, user_id)
    if user is None:
        raise ValueError("user_unavailable")
    fallback = ZoneInfo(user.timezone) if user.timezone else None
    periods = list_timezone_periods(db, user_id)
    starts = [period.effective_from for period in periods]
    zones = [ZoneInfo(period.timezone) for period in periods]

    def resolve(at: datetime) -> ZoneInfo | None:
        index = bisect_right(starts, at) - 1
        return zones[index] if index >= 0 else fallback

    return resolve
