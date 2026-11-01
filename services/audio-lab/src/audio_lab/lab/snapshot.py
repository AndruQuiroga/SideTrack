"""Read the listening snapshot and the owner's kept axes, and join plays to axis scores.

The snapshot is the CSV written by ``scripts/lab_snapshot.sql``. Plays join to scores by the
asset's SHA-256. A play that can't be placed on the axes is counted, with the reason, never dropped
silently.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from audio_lab.dimensions import DIMENSIONS_JSON, SCORES_CSV, DimensionsError
from audio_lab.dimensions_review import validate_decision

from .site import Unavailable

SNAPSHOT_COLUMNS = (
    "played_at",
    "artist",
    "title",
    "session_start",
    "session_end",
    "session_kind",
    "sha256",
    "doubtful_timing",
)
AUTOPLAY_KINDS = {"night_autoplay", "autoplay"}


class SnapshotError(ValueError):
    pass


@dataclass(frozen=True)
class Play:
    at: datetime
    artist: str
    title: str
    session_start: datetime | None
    session_end: datetime | None
    kind: str
    sha256: str
    doubtful: bool


def _time(value: str) -> datetime | None:
    if not value:
        return None
    moment = datetime.fromisoformat(value)
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _flag(value: str, line: int) -> bool:
    lowered = value.strip().lower()
    if lowered in {"t", "true", "1"}:
        return True
    if lowered in {"f", "false", "0", ""}:
        return False
    raise SnapshotError(f"line {line}: doubtful_timing must be true or false, not {value!r}")


def read_snapshot(path: Path) -> list[Play]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(SNAPSHOT_COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise SnapshotError(f"snapshot is missing columns: {', '.join(sorted(missing))}")
        plays = []
        for line, row in enumerate(reader, start=2):
            try:
                at = _time(row["played_at"])
                start, end = _time(row["session_start"]), _time(row["session_end"])
            except ValueError as exc:
                raise SnapshotError(f"line {line}: {exc}") from exc
            if at is None:
                raise SnapshotError(f"line {line}: played_at is empty")
            plays.append(
                Play(
                    at=at,
                    artist=row["artist"],
                    title=row["title"],
                    session_start=start,
                    session_end=end,
                    kind=row["session_kind"],
                    sha256=row["sha256"],
                    doubtful=_flag(row["doubtful_timing"], line),
                )
            )
    return plays


@dataclass(frozen=True)
class Axes:
    """The owner's kept axes and every analysed track's position on them."""

    ids: list[str]
    names: list[str]
    positions: dict[str, np.ndarray]  # sha256 -> one score per kept axis
    tracks: dict[str, tuple[str, str]]  # sha256 -> (artist, title)


def _axis_number(axis_id: str) -> int:
    return int(axis_id.removeprefix("axis"))


def load_axes(dimensions_dir: Path, decision_path: Path) -> Axes:
    """Kept axes from the decision file, validated against ``dimensions.json``.

    Raises ``Unavailable`` when the decision doesn't fit the run or keeps no axis.
    """

    try:
        report = json.loads((dimensions_dir / DIMENSIONS_JSON).read_text("utf-8"))
        decision = json.loads(decision_path.read_text("utf-8"))
        validate_decision(decision, report)
    except (DimensionsError, OSError, ValueError) as exc:
        raise Unavailable(f"the axis decision is not usable: {exc}") from exc
    kept = sorted(
        (a for a, e in decision["axes"].items() if e["decision"] == "keep"), key=_axis_number
    )
    if not kept:
        raise Unavailable("no axis is marked keep in the decision")
    positions: dict[str, np.ndarray] = {}
    tracks: dict[str, tuple[str, str]] = {}
    with (dimensions_dir / SCORES_CSV).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            positions[row["sha256"]] = np.array([float(row[axis]) for axis in kept])
            tracks[row["sha256"]] = (row["artist"], row["title"])
    return Axes(
        ids=kept,
        names=[decision["axes"][axis]["name"].strip() for axis in kept],
        positions=positions,
        tracks=tracks,
    )


@dataclass
class Joined:
    """Plays that sit on the axes, in time order, and a count of those that can't."""

    plays: list[Play]
    counts: dict[str, int] = field(default_factory=dict)


def join_plays(plays: list[Play], axes: Axes) -> Joined:
    """Keep plays whose asset has axis scores. Count the rest as ``no_audio`` or ``unmatched``.

    ``no_audio`` is a play with no linked asset; ``unmatched`` has an asset that isn't among the
    analysed tracks.
    """

    counts = {"plays": len(plays), "scored": 0, "no_audio": 0, "unmatched": 0}
    usable = []
    for play in plays:
        if not play.sha256:
            counts["no_audio"] += 1
        elif play.sha256 not in axes.positions:
            counts["unmatched"] += 1
        else:
            counts["scored"] += 1
            usable.append(play)
    usable.sort(key=lambda p: p.at)
    return Joined(usable, counts)
