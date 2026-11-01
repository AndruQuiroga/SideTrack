"""A blind listening page for the dimensions, and the check for the decision it exports.

One self-contained HTML file: no network, no audio server. Audio plays from local ``file://``
URIs of files the owner already holds. The page shows ten tracks from each end of every axis,
and never a score or a suggested name. Which end is shown first is fixed by the run, the seed
and the axis, so the page is the same every time it is generated.
"""

from __future__ import annotations

import csv
import hashlib
import json
from importlib import resources
from pathlib import Path

import numpy as np

from .dimensions import DIMENSIONS_JSON, SCORES_CSV, DimensionsError
from .manifest import read_manifest
from .seeds import ensure_outside_repo

PLACEHOLDER = "/*__DIMENSIONS_DATA__*/null"
PER_END = 10
CLIP_START = 0.35
DECISIONS = ("keep", "merge", "drop")


def _digest(*parts: object) -> bytes:
    return hashlib.sha256(":".join(str(p) for p in parts).encode()).digest()


def ends_swapped(run_id: str, seed: int, axis_id: str) -> bool:
    """Whether the axis's low end is shown as End A. Fixed by the run, not by the clock."""

    return bool(_digest(run_id, seed, axis_id)[0] & 1)


def _clip_uri(path: str, audio_dir: Path, duration_s: float | None) -> str | None:
    file = (audio_dir / path).resolve()
    if not file.is_file():
        return None
    return f"{file.as_uri()}#t={CLIP_START * (duration_s or 0):.1f}"


def build_data(dimensions_dir: Path, manifest_path: Path, audio_dir: Path) -> dict:
    report = json.loads((dimensions_dir / DIMENSIONS_JSON).read_text(encoding="utf-8"))
    with (dimensions_dir / SCORES_CSV).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assets = {a.sha256: a for a in read_manifest(manifest_path)}
    if not report["axes"]:
        raise DimensionsError("this run has no stable axes to review")
    if len(rows) < 2 * PER_END:
        raise DimensionsError(f"{len(rows)} tracks are too few to show {PER_END} from each end")

    axes = []
    for axis in report["axes"]:
        scores = np.array([float(row[axis["id"]]) for row in rows])
        order = np.argsort(scores, kind="stable")
        ends = {"low": order[:PER_END], "high": order[-PER_END:]}
        shown = {}
        for name, picked in ends.items():
            # Shuffled so that position within an end doesn't hint at how extreme a track is.
            rng = np.random.default_rng(
                int.from_bytes(_digest(report["run_id"], axis["id"], name)[:8])
            )
            tracks = []
            for row in (rows[i] for i in rng.permutation(picked)):
                asset = assets.get(row["sha256"])
                uri = _clip_uri(asset.path, audio_dir, asset.duration_s) if asset else None
                tracks.append({"audio": uri})
            shown[name] = tracks
        first, second = (
            ("low", "high")
            if ends_swapped(report["run_id"], report["seed"], axis["id"])
            else ("high", "low")
        )
        axes.append({"id": axis["id"], "a": shown[first], "b": shown[second]})
    return {"run_id": report["run_id"], "axes": axes}


def render(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = resources.files(__package__).joinpath("dimensions_review.html").read_text("utf-8")
    return page.replace(PLACEHOLDER, payload)


def write_review(dimensions_dir: Path, manifest_path: Path, audio_dir: Path, out: Path) -> Path:
    ensure_outside_repo(out)
    page = render(build_data(dimensions_dir, manifest_path, audio_dir))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


def validate_decision(decision: dict, report: dict) -> dict:
    """Check an exported decision against ``dimensions.json``; raise naming the offending axis."""

    run_id = report["run_id"]
    if decision.get("run_id") != run_id:
        raise DimensionsError(f"decision is for run {decision.get('run_id')!r}, not {run_id}")
    known = {axis["id"] for axis in report["axes"]}
    chosen = decision.get("axes")
    if not isinstance(chosen, dict):
        raise DimensionsError("decision has no axes")
    for axis in chosen:
        if axis not in known:
            raise DimensionsError(f"decision names axis {axis}, which is not in run {run_id}")
    for axis in sorted(known):
        if axis not in chosen:
            raise DimensionsError(f"axis {axis} has no decision")
    for axis, entry in chosen.items():
        verdict = entry.get("decision")
        if verdict not in DECISIONS:
            raise DimensionsError(f"axis {axis}: decision must be one of {', '.join(DECISIONS)}")
        if verdict == "keep" and not str(entry.get("name", "")).strip():
            raise DimensionsError(f"axis {axis}: a kept axis needs your name for it")
        if verdict == "merge":
            target = entry.get("merge_into")
            if target not in known or target == axis:
                raise DimensionsError(f"axis {axis}: merge_into must be another axis in the run")
    return {
        verdict: sorted(a for a, e in chosen.items() if e["decision"] == verdict)
        for verdict in DECISIONS
    }
