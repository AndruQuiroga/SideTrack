"""Synthetic dimensions runs and listening snapshots for the lab's tests. Never real data."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np

from audio_lab.lab.snapshot import SNAPSHOT_COLUMNS


def sha(index: int) -> str:
    return f"{index:064x}"


def write_axes(
    root: Path,
    positions: np.ndarray,
    *,
    names: dict[str, str] | None = None,
    decisions: dict[str, str] | None = None,
    artists: list[str] | None = None,
) -> tuple[Path, Path]:
    """Write dimensions.json, scores.csv and a decision file for tracks at ``positions``.

    ``positions`` has one row per track and one column per axis. Track ``i`` has sha ``sha(i)``.
    Returns (dimensions_dir, decision_path).
    """

    root.mkdir(parents=True, exist_ok=True)
    count = positions.shape[1]
    ids = [f"axis{k + 1}" for k in range(count)]
    (root / "dimensions.json").write_text(
        json.dumps({"run_id": "run-test", "seed": 0, "axes": [{"id": i} for i in ids]}),
        encoding="utf-8",
    )
    with (root / "scores.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["sha256", "artist", "title", "kind", *ids])
        for i, row in enumerate(positions):
            artist = artists[i] if artists else f"Artist {i}"
            writer.writerow([sha(i), artist, f"Title {i}", "full", *[f"{v:.6f}" for v in row]])
    names = names or {}
    decisions = decisions or {}
    decision = {
        "run_id": "run-test",
        "decided_at": "2026-11-01",
        "axes": {
            i: {
                "decision": decisions.get(i, "keep"),
                "name": names.get(i, f"Name {i}") if decisions.get(i, "keep") == "keep" else "",
                "merge_into": "",
            }
            for i in ids
        },
    }
    path = root / "dimensions-decision.json"
    path.write_text(json.dumps(decision), encoding="utf-8")
    return root, path


def write_snapshot(path: Path, rows: list[dict]) -> Path:
    """Rows hold ``at`` (datetime), ``track`` (index into the axes file, or None) and optionals.

    Each row may carry ``kind``, ``doubtful``, ``artist`` and ``title``. A play's session is a
    one-second window at its own time unless ``session`` (start, end) is given.
    """

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(SNAPSHOT_COLUMNS)
        for row in rows:
            at: datetime = row["at"]
            start, end = row.get("session", (at, at))
            writer.writerow(
                [
                    at.isoformat(sep=" "),
                    row.get("artist", f"Artist {row['track']}"),
                    row.get("title", f"Title {row['track']}"),
                    start.isoformat(sep=" "),
                    end.isoformat(sep=" "),
                    row.get("kind", "unclassified"),
                    "" if row["track"] is None else sha(row["track"]),
                    "t" if row.get("doubtful") else "f",
                ]
            )
    return path
