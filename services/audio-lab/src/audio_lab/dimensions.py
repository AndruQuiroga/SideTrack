"""The independent sound dimensions of one listener's own tracks.

One vector per track, principal components kept only above a shuffled baseline, checked for
stability by resampling tracks, rotated for listening and compared with the mood scores.
Everything here is a linear view of the embeddings; nothing is a fact about the listener.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .manifest import Asset, _norm, read_manifest
from .runs import RUN_JSON, load_run


class DimensionsError(Exception):
    pass


def read_excluded_seeds(paths: list[Path]) -> set[str]:
    """Normalised ``artist|title`` keys from seed CSVs (``seeds.csv``, ``control-seeds.csv``)."""

    keys: set[str] = set()
    for path in paths:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not {"artist", "title"} <= set(reader.fieldnames or []):
                raise DimensionsError(f"{path} needs artist and title columns")
            keys.update(f"{_norm(row['artist'])}|{_norm(row['title'])}" for row in reader)
    return keys


@dataclass
class Selection:
    """One vector per track: ``hashes[i]`` is the asset behind ``vectors[i]``."""

    hashes: list[str]
    vectors: np.ndarray
    assets: list[Asset]
    dropped: dict[str, int] = field(default_factory=dict)

    def counts(self) -> dict:
        return {"tracks": len(self.hashes), "dropped": dict(self.dropped)}


def _model_vectors(table, model: str) -> dict[str, np.ndarray]:
    names = table.column("model").to_numpy(zero_copy_only=False)
    rows = table.filter(names == model)
    hashes = rows.column("sha256").to_pylist()
    matrix = np.asarray(rows.column("vector").to_pylist(), dtype=float)
    return dict(zip(hashes, matrix, strict=True))


def select_tracks(
    table, manifest: list[Asset], model: str, exclude_seeds: set[str] | None = None
) -> Selection:
    """Keep one asset per track, a full one if there is one, and drop listed control seeds."""

    excluded = exclude_seeds or set()
    vectors = _model_vectors(table, model)
    known = {asset.sha256 for asset in manifest}
    dropped = {
        "excluded_seed": 0,
        "preview_superseded": 0,
        "duplicate_full": 0,
        "not_in_manifest": sum(1 for sha in vectors if sha not in known),
    }

    by_track: dict[str, list[Asset]] = {}
    seen: set[str] = set()
    for asset in manifest:
        if asset.sha256 not in vectors or asset.sha256 in seen:
            continue
        seen.add(asset.sha256)
        by_track.setdefault(asset.seed, []).append(asset)

    chosen: list[Asset] = []
    for assets in by_track.values():
        if any(f"{_norm(a.artist)}|{_norm(a.title)}" in excluded for a in assets):
            dropped["excluded_seed"] += len(assets)
            continue
        fulls = sorted((a for a in assets if a.kind == "full"), key=lambda a: a.sha256)
        keep = fulls[0] if fulls else min(assets, key=lambda a: a.sha256)
        dropped["duplicate_full"] += max(len(fulls) - 1, 0)
        dropped["preview_superseded"] += sum(1 for a in assets if a.kind == "preview" and fulls)
        chosen.append(keep)

    chosen.sort(key=lambda a: a.sha256)
    if not chosen:
        raise DimensionsError(f"no tracks left to analyse for model {model}")
    matrix = np.stack([vectors[a.sha256] for a in chosen])
    return Selection([a.sha256 for a in chosen], matrix, chosen, dropped)


def load_selection(
    run_dir: Path, manifest_path: Path, model: str, exclude_seeds: list[Path] | None = None
) -> tuple[dict, Selection]:
    if not (run_dir / RUN_JSON).is_file():
        raise DimensionsError(f"{run_dir} is not a run directory")
    record, table = load_run(run_dir)
    if record["models"].get(model, {}).get("status") != "ok":
        raise DimensionsError(f"model {model} is not in run {record['run_id']}")
    keys = read_excluded_seeds(exclude_seeds or [])
    return record, select_tracks(table, read_manifest(manifest_path), model, keys)
