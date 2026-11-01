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


SHUFFLES = 100
BASELINE_PERCENTILE = 95.0


def _orient(axes: np.ndarray) -> np.ndarray:
    """Flip each row's sign so its largest-magnitude entry is positive (a stable convention)."""

    largest = np.argmax(np.abs(axes), axis=1)
    signs = np.sign(axes[np.arange(len(axes)), largest])
    return axes * np.where(signs == 0, 1.0, signs)[:, None]


def principal_components(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Centred SVD: eigenvalues of the covariance (descending) and unit axes as rows."""

    centred = x - x.mean(axis=0)
    _, singular, axes = np.linalg.svd(centred, full_matrices=False)
    return singular**2 / max(len(x) - 1, 1), _orient(axes)


def parallel_analysis(
    x: np.ndarray, rng: np.random.Generator, shuffles: int = SHUFFLES
) -> tuple[int, np.ndarray]:
    """How many leading components beat the 95th percentile of column-shuffled copies.

    Returns the count and the threshold for every component. The count stops at the first
    component that fails, so a noisy tail can't revive a rejected one.
    """

    eigenvalues, _ = principal_components(x)
    null = np.zeros((shuffles, len(eigenvalues)))
    shuffled = np.empty_like(x)
    for trial in range(shuffles):
        for column in range(x.shape[1]):
            shuffled[:, column] = rng.permutation(x[:, column])
        null[trial] = principal_components(shuffled)[0]
    threshold = np.percentile(null, BASELINE_PERCENTILE, axis=0)
    beaten = eigenvalues > threshold
    kept = len(beaten) if beaten.all() else int(np.argmin(beaten))
    return kept, threshold


RESAMPLES = 200
STABLE_AT = 0.80


def stability(
    x: np.ndarray, axes: np.ndarray, rng: np.random.Generator, resamples: int = RESAMPLES
) -> np.ndarray:
    """Median absolute cosine between each full-fit axis and the same-rank axis of a resample.

    Matching by rank, not by best fit, is deliberate: two axes with near-equal variance trade
    places and rotate into each other between resamples, and that is exactly the instability a
    listener would meet. The sign of a principal axis is arbitrary, hence the absolute value.
    """

    kept = len(axes)
    cosines = np.zeros((resamples, kept))
    for trial in range(resamples):
        rows = rng.integers(len(x), size=len(x))
        _, resampled = principal_components(x[rows])
        cosines[trial] = np.abs(np.einsum("kd,kd->k", axes, resampled[:kept]))
    return np.median(cosines, axis=0)


@dataclass
class Components:
    """Principal components of the tracks, the kept ones and how stable each kept one is."""

    eigenvalues: np.ndarray
    axes: np.ndarray  # every component, as rows
    threshold: np.ndarray  # the shuffled baseline per component
    kept: int
    stability: np.ndarray  # length ``kept``

    @property
    def stable(self) -> list[int]:
        return [i for i in range(self.kept) if self.stability[i] >= STABLE_AT]


def analyse(x: np.ndarray, seed: int = 0) -> Components:
    """Same input and seed give the same result: every random draw comes from one generator."""

    rng = np.random.default_rng(seed)
    eigenvalues, axes = principal_components(x)
    kept, threshold = parallel_analysis(x, rng)
    robust = stability(x, axes[:kept], rng) if kept else np.zeros(0)
    return Components(eigenvalues, axes, threshold, kept, robust)


def varimax_rotation(
    loadings: np.ndarray, iterations: int = 500, tolerance: float = 1e-9
) -> np.ndarray:
    """The orthogonal matrix that makes each column of ``loadings`` load on few variables."""

    variables, count = loadings.shape
    rotation = np.eye(count)
    total = 0.0
    for _ in range(iterations):
        rotated = loadings @ rotation
        spread = rotated**3 - rotated @ np.diag((rotated**2).sum(axis=0)) / variables
        u, singular, vt = np.linalg.svd(loadings.T @ spread)
        rotation = u @ vt
        previous, total = total, float(singular.sum())
        if previous and total < previous * (1 + tolerance):
            break
    return rotation


def rotate(axes: np.ndarray, eigenvalues: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Varimax over the given principal axes (rows) and their eigenvalues.

    Returns unit axes as rows and each axis's variance, largest first. An orthogonal rotation
    of an orthonormal basis keeps their total variance.
    """

    if len(axes) < 2:
        return axes.copy(), eigenvalues.copy()
    rotation = varimax_rotation(axes.T * np.sqrt(eigenvalues))
    coordinates = rotation.T  # rows: the rotated axes written in the principal-axis basis
    variances = (coordinates**2) @ eigenvalues  # principal scores are uncorrelated
    order = np.argsort(-variances, kind="stable")
    return _orient((coordinates @ axes)[order]), variances[order]
