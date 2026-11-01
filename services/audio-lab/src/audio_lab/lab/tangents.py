"""Find tangents: runs of sessions that leave the listener's usual sound, and what they did next.

Sessions are placed on the owner's kept axes. Each is compared with a trailing baseline of the
previous 90 days of sessions. A run of deviating sessions that comes back is a tangent; one still
away after 45 days is a drift (a candidate era). Silence ends a run as a gap, never as a return.

Everything here is an estimate of a change in *sound*. It says nothing about why.

Choices the design leaves open, fixed here so results are reproducible:

- Axes are measured in units of the analysed library's own spread, so a high-variance axis doesn't
  dominate. ``deviation`` is the distance from the baseline mean in those units, divided by the
  baseline's root-mean-square distance from its own mean.
- A session leaving a run's baseline pool: sessions in an open run and in a returned tangent don't
  count towards the baseline; a drift's sessions do once it is declared, so the baseline catches up.
- A session's time is its start. A run ends at the end of its last deviating session.
"""

from __future__ import annotations

import bisect
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

from .snapshot import AUTOPLAY_KINDS, Axes, Play

PRESETS = {"strict": 2.5, "normal": 2.0, "loose": 1.5}
TOP_TRACKS = 5
_EPS = 1e-9


@dataclass(frozen=True)
class Params:
    min_session_plays: int = 3
    baseline_days: int = 90
    min_baseline: int = 10
    min_run_sessions: int = 2
    min_run_plays: int = 8
    return_streak: int = 3
    drift_days: int = 45
    gap_days: int = 30


DEFAULTS = Params()


@dataclass(frozen=True)
class Session:
    start: datetime
    end: datetime
    position: np.ndarray  # play-weighted mean, in library-spread units
    plays: int
    tracks: tuple[tuple[str, int], ...]  # (sha256, plays), most played first


@dataclass
class Sessions:
    sessions: list[Session]
    skips: dict[str, int] = field(default_factory=dict)


def scale_of(axes: Axes) -> np.ndarray:
    """The library's spread on each kept axis, floored so a flat axis can't divide by zero."""

    matrix = np.stack(list(axes.positions.values()))
    spread = matrix.std(axis=0)
    return np.where(spread > _EPS, spread, 1.0)


def session_positions(plays: list[Play], axes: Axes, params: Params = DEFAULTS) -> Sessions:
    """Group plays into sessions and place each on the kept axes.

    A session's position is the mean of the positions of its plays that have audio, so a track
    played three times counts three times. Skipped sessions are counted by reason, one reason each:
    ``autoplay``, ``doubtful`` (timing), then ``too_few_plays`` (under 3 plays with axis scores).
    """

    scale = scale_of(axes)
    grouped: dict[tuple[datetime, datetime], list[Play]] = {}
    no_session = 0
    for play in plays:
        if play.session_start is None or play.session_end is None:
            no_session += 1
            continue
        grouped.setdefault((play.session_start, play.session_end), []).append(play)

    skips = {"sessions": len(grouped), "autoplay": 0, "doubtful": 0, "too_few_plays": 0}
    sessions = []
    for (start, end), members in sorted(grouped.items()):
        if any(p.kind in AUTOPLAY_KINDS for p in members):
            skips["autoplay"] += 1
            continue
        if any(p.doubtful for p in members):
            skips["doubtful"] += 1
            continue
        scored = [p for p in members if p.sha256 in axes.positions]
        if len(scored) < params.min_session_plays:
            skips["too_few_plays"] += 1
            continue
        position = np.mean([axes.positions[p.sha256] for p in scored], axis=0) / scale
        counts = Counter(p.sha256 for p in scored)
        ranked = tuple(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
        sessions.append(Session(start, end, position, len(scored), ranked))
    skips["used"] = len(sessions)
    if no_session:
        skips["plays_without_session"] = no_session
    return Sessions(sessions, skips)


@dataclass
class _Run:
    sessions: list[Session]
    base_mean: np.ndarray
    peak: float
    returned_at: datetime | None = None


def _qualifies(run: _Run, params: Params) -> bool:
    return (
        len(run.sessions) >= params.min_run_sessions
        and sum(s.plays for s in run.sessions) >= params.min_run_plays
    )


def _describe(run: _Run, kind: str, ended: str, axes: Axes, scale: np.ndarray) -> dict:
    mean = np.mean([s.position for s in run.sessions], axis=0)
    shift = mean - run.base_mean
    moved = int(np.argmax(np.abs(shift)))
    plays: Counter[str] = Counter()
    for session in run.sessions:
        plays.update(dict(session.tracks))
    top = sorted(plays.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_TRACKS]
    return {
        "kind": kind,
        "ended": ended,
        "start": run.sessions[0].start.isoformat(),
        "end": run.sessions[-1].end.isoformat(),
        "returned_at": run.returned_at.isoformat() if run.returned_at else None,
        "peak_deviation": round(run.peak, 3),
        "sessions": len(run.sessions),
        "plays": sum(s.plays for s in run.sessions),
        "axis": axes.ids[moved],
        "axis_name": axes.names[moved],
        "side": 1 if shift[moved] >= 0 else -1,
        "shifts": [
            {"axis": axes.ids[i], "name": axes.names[i], "shift": round(float(shift[i]), 3)}
            for i in range(len(axes.ids))
        ],
        "top_tracks": [
            {
                "sha256": sha,
                "artist": axes.tracks[sha][0],
                "title": axes.tracks[sha][1],
                "plays": count,
            }
            for sha, count in top
        ],
    }


def detect(
    found: Sessions,
    axes: Axes,
    threshold: float,
    data_end: datetime | None = None,
    params: Params = DEFAULTS,
) -> dict:
    """Branches and gaps for one threshold.

    ``data_end`` is the time of the last play in the snapshot; a run still open when silence has
    reached it ends as a gap, otherwise it is left ``open`` (still going when the data stops).
    """

    scale = scale_of(axes)
    pool_times: list[datetime] = []
    pool: list[np.ndarray] = []
    branches: list[dict] = []
    gaps: list[dict] = []
    run: _Run | None = None
    streak = 0
    previous: Session | None = None
    no_baseline = 0

    def add_to_pool(session: Session) -> None:
        index = bisect.bisect_right(pool_times, session.start)
        pool_times.insert(index, session.start)
        pool.insert(index, session.position)

    def close(kind_if_kept: str, ended: str) -> None:
        nonlocal run, streak
        assert run is not None
        if _qualifies(run, params):
            branches.append(_describe(run, kind_if_kept, ended, axes, scale))
            # A returned tangent is the exception to the usual sound; it stays out of the baseline.
            keep_out = kind_if_kept == "tangent"
        else:
            keep_out = False
        if not keep_out:
            for session in run.sessions:
                add_to_pool(session)
        run, streak = None, 0

    for session in found.sessions:
        if previous is not None and session.start - previous.end >= timedelta(days=params.gap_days):
            gaps.append(
                {
                    "start": previous.end.isoformat(),
                    "end": session.start.isoformat(),
                    "days": (session.start - previous.end).days,
                }
            )
            if run is not None:
                close("open", "gap")
        previous = session

        low = bisect.bisect_left(pool_times, session.start - timedelta(days=params.baseline_days))
        high = bisect.bisect_left(pool_times, session.start)
        window = np.array(pool[low:high])
        if len(window) < params.min_baseline:
            no_baseline += 1
            add_to_pool(session)
            continue
        mean = window.mean(axis=0)
        spread = float(np.sqrt(((window - mean) ** 2).sum(axis=1).mean()))
        distance = float(np.linalg.norm(session.position - mean))
        deviation = distance / max(spread, _EPS)

        if deviation >= threshold:
            if run is None:
                run = _Run([session], mean, deviation)
            else:
                run.sessions.append(session)
                run.peak = max(run.peak, deviation)
            streak = 0
            run.returned_at = None
        elif run is not None:
            add_to_pool(session)
            streak += 1
            if streak == 1:
                run.returned_at = session.start
            if streak >= params.return_streak:
                close("tangent", "returned")
        else:
            add_to_pool(session)

        if run is not None and session.start - run.sessions[0].start >= timedelta(
            days=params.drift_days
        ):
            close("drift", "not_returned")

    if previous is not None and data_end is not None:
        if data_end - previous.end >= timedelta(days=params.gap_days):
            gaps.append(
                {
                    "start": previous.end.isoformat(),
                    "end": data_end.isoformat(),
                    "days": (data_end - previous.end).days,
                }
            )
            if run is not None:
                close("open", "gap")
    if run is not None:
        close("open", "data_end")
    skips = dict(found.skips)
    skips["no_baseline"] = no_baseline
    return {"threshold": threshold, "branches": branches, "gaps": gaps, "skips": skips}


def find_tangents(
    plays: list[Play], axes: Axes, params: Params = DEFAULTS, data_end: datetime | None = None
) -> dict:
    """Every preset's result over the same sessions, keyed by preset name."""

    found = session_positions(plays, axes, params)
    end = data_end or (max(p.at for p in plays) if plays else None)
    return {
        name: detect(found, axes, threshold, end, params) for name, threshold in PRESETS.items()
    }
