"""Forgotten favourites: tracks played a lot in some past window and not played since.

A "favourite" here is a play-count rule over the listener's own history, not a love: nothing
in this module stores or infers one. The rule is versioned and its values travel with every
result so a reader can see exactly what was counted.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from sidetrack.catalog import Track
from sidetrack.identity import timezone_resolver
from sidetrack.listening.listenbrainz import coverage_state
from sidetrack.listening.models import ImportCoverage, ListenEvent
from sidetrack.listening.sessions import effective_kind, list_sessions

RULE_VERSION = "forgotten-v1"


@dataclass(frozen=True)
class Rules:
    """N plays within W days is a past favourite; none in M days is forgotten.

    K plays on D distinct days in the last M days show the history is active enough to
    call anything forgotten.
    """

    min_plays: int = 8  # N
    window_days: int = 90  # W
    forgotten_days: int = 365  # M
    min_recent_plays: int = 50  # K
    min_recent_days: int = 20  # D

    def values(self) -> dict[str, Any]:
        return {"rule_version": RULE_VERSION, **asdict(self)}


DEFAULT_RULES = Rules()


@dataclass(frozen=True)
class Peak:
    plays: int
    start: datetime
    end: datetime


def peak_window(times: Iterable[datetime], window_days: int) -> Peak | None:
    """The W-day window holding the most plays; the earliest wins a tie.

    A window starts at a play and covers `window_days` days, end excluded. `start` and
    `end` are its first and last play.
    """

    ordered = sorted(times)
    if not ordered:
        return None
    span = timedelta(days=window_days)
    best = Peak(1, ordered[0], ordered[0])
    left = 0
    for right, at in enumerate(ordered):
        while at - ordered[left] >= span:
            left += 1
        count = right - left + 1
        if count > best.plays:
            best = Peak(count, ordered[left], at)
    return best


def find_forgotten(
    plays: Iterable[tuple[UUID, datetime]], now: datetime, rules: Rules = DEFAULT_RULES
) -> list[dict[str, Any]]:
    """Tracks with a qualifying peak and no play in the last M days, most plays first.

    `plays` are the included plays only. This applies the play-count rule; whether the
    history is complete and active enough to use it is decided by the caller.
    """

    by_track: dict[UUID, list[datetime]] = defaultdict(list)
    for track_id, at in plays:
        by_track[track_id].append(at)
    cutoff = now - timedelta(days=rules.forgotten_days)
    found = []
    for track_id, times in by_track.items():
        last = max(times)
        if last > cutoff:
            continue
        peak = peak_window(times, rules.window_days)
        if peak is None or peak.plays < rules.min_plays:
            continue
        found.append(
            {
                "track_id": track_id,
                "peak_plays": peak.plays,
                "peak_start": peak.start,
                "peak_end": peak.end,
                "last_played_at": last,
                "total_plays": len(times),
            }
        )
    found.sort(key=lambda row: (-row["peak_plays"], row["peak_start"], str(row["track_id"])))
    return found


_AUTOPLAY_KINDS = frozenset({"night_autoplay", "autoplay"})
_SESSION_PAGE = 1000


@dataclass(frozen=True)
class IncludedPlays:
    """The plays the rule counts, and what was left out or counted without a timezone."""

    plays: list[tuple[UUID, datetime]]
    excluded_autoplay: int
    unknown_session: int


def _session_kinds(db: Session, user_id: UUID) -> dict[UUID, str]:
    kinds: dict[UUID, str] = {}
    offset = 0
    while True:
        page = list_sessions(db, user_id, limit=_SESSION_PAGE, offset=offset)
        for session, override in page:
            kinds[session.id] = effective_kind(session, override)
        if len(page) < _SESSION_PAGE:
            return kinds
        offset += _SESSION_PAGE


def included_plays(db: Session, user_id: UUID, *, include_autoplay: bool = False) -> IncludedPlays:
    """The user's plays by effective session classification.

    Plays in sessions whose effective kind is autoplay (the rule's flag or the user's
    override, so a `keep` override counts) are left out unless asked for, and counted.
    Plays in `unknown` sessions are included and counted, as are plays not yet in any
    session, which have no classification either.
    """

    kinds = _session_kinds(db, user_id)
    rows = db.execute(
        select(ListenEvent.track_id, ListenEvent.played_at, ListenEvent.session_id).where(
            ListenEvent.user_id == user_id
        )
    )
    plays: list[tuple[UUID, datetime]] = []
    excluded = unknown = 0
    for track_id, played_at, session_id in rows:
        kind = kinds.get(session_id, "unknown") if session_id else "unknown"
        if kind in _AUTOPLAY_KINDS and not include_autoplay:
            excluded += 1
            continue
        unknown += kind == "unknown"
        plays.append((track_id, played_at))
    return IncludedPlays(plays=plays, excluded_autoplay=excluded, unknown_session=unknown)


# Imported history ends at the last listen, not at the moment of import, so "covers the
# recent window" allows the newest listen to be a few days old.
COVERAGE_SLACK = timedelta(days=7)
NOT_IMPORTED = "not_imported"
COVERAGE_GAP = "coverage_gap"
INSUFFICIENT_HISTORY = "insufficient_history"
NONE_FOUND = "none_found"
FOUND = "found"


def forgotten_favourites(
    db: Session,
    user_id: UUID,
    *,
    include_autoplay: bool = False,
    now: datetime | None = None,
    rules: Rules = DEFAULT_RULES,
) -> dict[str, Any]:
    """The user's forgotten favourites, or the reason none can be named.

    `state` is `not_imported` (no committed import), `coverage_gap` (imported history does
    not reach back M days and forward to now), `insufficient_history` (too little recent
    activity to call anything forgotten), `none_found` or `found`. Only `found` has tracks.
    """

    now = now or datetime.now(UTC)
    coverage = _coverage_range(db, user_id)
    result: dict[str, Any] = {
        "state": NOT_IMPORTED,
        "rules": rules.values(),
        "include_autoplay": include_autoplay,
        "coverage_start": coverage[0] if coverage else None,
        "coverage_end": coverage[1] if coverage else None,
        "recent_plays": None,
        "recent_days": None,
        "excluded_autoplay_plays": 0,
        "unknown_session_plays": 0,
        "tracks": [],
    }
    if coverage is None:
        return result
    recent_from = now - timedelta(days=rules.forgotten_days)
    if coverage_state(db, user_id, recent_from, now - COVERAGE_SLACK) != "covered":
        result["state"] = COVERAGE_GAP
        return result

    included = included_plays(db, user_id, include_autoplay=include_autoplay)
    result["excluded_autoplay_plays"] = included.excluded_autoplay
    result["unknown_session_plays"] = included.unknown_session
    zone = timezone_resolver(db, user_id)
    recent = [at for _, at in included.plays if recent_from < at <= now]
    days = {at.astimezone(zone(at) or UTC).date() for at in recent}
    result["recent_plays"], result["recent_days"] = len(recent), len(days)
    if len(recent) < rules.min_recent_plays or len(days) < rules.min_recent_days:
        result["state"] = INSUFFICIENT_HISTORY
        return result

    found = find_forgotten(included.plays, now, rules)
    tracks = db.scalars(select(Track).where(Track.id.in_([row["track_id"] for row in found])))
    by_id = {track.id: track for track in tracks}
    for row in found:
        track = by_id[row["track_id"]]
        row.update(title=track.title, artist_name=track.artist_name)
    result["tracks"] = found
    result["state"] = FOUND if found else NONE_FOUND
    return result


def _coverage_range(db: Session, user_id: UUID) -> tuple[datetime, datetime] | None:
    rows = db.scalars(select(ImportCoverage).where(ImportCoverage.user_id == user_id)).all()
    if not rows:
        return None
    return min(r.earliest_played_at for r in rows), max(r.latest_played_at for r in rows)
