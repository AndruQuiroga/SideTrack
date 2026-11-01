"""Group listens into sessions and flag likely sleep-tab autoplay by a reviewable rule."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, tzinfo
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from sidetrack.identity import User
from sidetrack.listening.models import ListenEvent, ListenSession, ListenSessionOverride

SESSION_GAP = timedelta(minutes=30)
NIGHT_RULE = "night-v1"
_NIGHT_MIN_DURATION = timedelta(hours=1)
_NIGHT_MIN_LISTENS = 12


def classify(started: datetime, ended: datetime, count: int, zone: tzinfo | None) -> str:
    """`night-v1`: starts 22:00-04:00 local, lasts an hour or more, 12+ listens."""

    if zone is None:
        return "unknown"
    hour = started.astimezone(zone).hour
    night = (hour >= 22 or hour < 4) and ended - started >= _NIGHT_MIN_DURATION
    return "night_autoplay" if night and count >= _NIGHT_MIN_LISTENS else "unclassified"


def _group(played: list[datetime]) -> list[tuple[datetime, datetime, int]]:
    groups: list[tuple[datetime, datetime, int]] = []
    for at in played:
        if groups and at - groups[-1][1] <= SESSION_GAP:
            start, _, count = groups[-1]
            groups[-1] = (start, at, count + 1)
        else:
            groups.append((at, at, 1))
    return groups


def sessionize(
    db: Session,
    user_id: UUID,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Rebuild the sessions touching a played-time range, or all of them without one.

    Sessions within the gap of the range are rebuilt too, so new listens extend or join
    them. The caller owns the transaction.
    """

    user = db.get(User, user_id)
    if user is None:
        raise ValueError("user_unavailable")
    zone = ZoneInfo(user.timezone) if user.timezone else None
    stale = select(ListenSession).where(ListenSession.user_id == user_id)
    first, last = since, until
    if since is not None:
        stale = stale.where(ListenSession.ended_at >= since - SESSION_GAP)
        if until is not None:
            stale = stale.where(ListenSession.started_at <= until + SESSION_GAP)
    rows = db.scalars(stale).all()
    if since is not None:
        first = min([since, *(row.started_at for row in rows)])
        last = None if until is None else max([until, *(row.ended_at for row in rows)])
    if rows:
        db.execute(delete(ListenSession).where(ListenSession.id.in_([row.id for row in rows])))

    played = select(ListenEvent.played_at).where(ListenEvent.user_id == user_id)
    if first is not None:
        played = played.where(ListenEvent.played_at >= first)
    if last is not None:
        played = played.where(ListenEvent.played_at <= last)
    now = datetime.now(UTC)
    built = []
    for started, ended, count in _group(list(db.scalars(played.order_by(ListenEvent.played_at)))):
        session = ListenSession(
            user_id=user_id,
            started_at=started,
            ended_at=ended,
            listen_count=count,
            kind=classify(started, ended, count, zone),
            rule_version=NIGHT_RULE,
            computed_at=now,
        )
        db.add(session)
        built.append(session)
    db.flush()
    for session in built:
        db.execute(
            update(ListenEvent)
            .where(
                ListenEvent.user_id == user_id,
                ListenEvent.played_at >= session.started_at,
                ListenEvent.played_at <= session.ended_at,
            )
            .values(session_id=session.id)
            .execution_options(synchronize_session=False)
        )
    orphaned = db.scalar(
        select(func.count())
        .select_from(ListenSessionOverride)
        .outerjoin(
            ListenSession,
            and_(
                ListenSession.user_id == ListenSessionOverride.user_id,
                ListenSession.started_at == ListenSessionOverride.started_at,
                ListenSession.ended_at == ListenSessionOverride.ended_at,
            ),
        )
        .where(ListenSessionOverride.user_id == user_id, ListenSession.id.is_(None))
    )
    return {
        "sessions": len(built),
        "night_autoplay": sum(session.kind == "night_autoplay" for session in built),
        "unknown": sum(session.kind == "unknown" for session in built),
        "rule_version": NIGHT_RULE,
        "notes": ["timezone_missing"] if zone is None else [],
        "override_orphaned": orphaned,
    }


def effective_kind(session: ListenSession, override: str | None) -> str:
    """The user's review if there is one, otherwise the rule flag."""

    return override or session.kind


def list_sessions(
    db: Session, user_id: UUID, *, limit: int = 50, offset: int = 0
) -> list[tuple[ListenSession, str | None]]:
    """Newest first, each with its override. Later changes read `effective_kind`."""

    rows = db.execute(
        select(ListenSession, ListenSessionOverride.override)
        .outerjoin(
            ListenSessionOverride,
            and_(
                ListenSessionOverride.user_id == ListenSession.user_id,
                ListenSessionOverride.started_at == ListenSession.started_at,
                ListenSessionOverride.ended_at == ListenSession.ended_at,
            ),
        )
        .where(ListenSession.user_id == user_id)
        .order_by(ListenSession.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [(session, override) for session, override in rows]


def set_override(db: Session, session: ListenSession, override: str | None) -> None:
    """Set or clear a review. The caller owns the transaction."""

    boundaries = {
        "user_id": session.user_id,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
    }
    if override is None:
        db.execute(
            delete(ListenSessionOverride).where(
                *(getattr(ListenSessionOverride, key) == value for key, value in boundaries.items())
            )
        )
        return
    now = datetime.now(UTC)
    db.execute(
        insert(ListenSessionOverride)
        .values(**boundaries, override=override, set_at=now)
        .on_conflict_do_update(
            index_elements=list(boundaries), set_={"override": override, "set_at": now}
        )
    )
