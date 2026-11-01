"""Forgotten favourites: tracks played a lot in some past window and not played since.

A "favourite" here is a play-count rule over the listener's own history, not a love: nothing
in this module stores or infers one. The rule is versioned and its values travel with every
result so a reader can see exactly what was counted.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

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
