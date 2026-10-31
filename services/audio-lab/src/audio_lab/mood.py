"""Linear valence and arousal probes over a run's embeddings, scored out of sample."""

from __future__ import annotations

import csv
import hashlib
import json
from itertools import combinations
from pathlib import Path

import numpy as np

from .manifest import read_manifest
from .runs import RUN_JSON, load_run
from .seeds import ensure_outside_repo

DIMENSIONS = ("valence", "arousal")
ALPHAS = np.logspace(-1, 6, 15)
FOLDS = 5
INNER_FOLDS = 3
REPEATS = 5
BOOTSTRAPS = 2000
MIN_CLIPS_PER_FOLD = 10
MOOD_JSON = "mood.json"
PREDICTION_COLUMNS = ("sha256", "artist", "title", "model", "valence", "arousal")


class MoodError(Exception):
    pass


def read_mood_labels(path: Path) -> dict[str, tuple[float, float, str]]:
    """Asset hash → valence, arousal and group."""

    with path.open(encoding="utf-8", newline="") as handle:
        return {
            row["sha256"]: (float(row["valence"]), float(row["arousal"]), row["group"])
            for row in csv.DictReader(handle)
        }


def group_folds(groups: np.ndarray, folds: int, rng: np.random.Generator) -> np.ndarray:
    """Each clip's fold, balanced by size, with every clip of a group in the same fold."""

    _, inverse = np.unique(groups, return_inverse=True)
    sizes = np.bincount(inverse)
    shuffled = rng.permutation(len(sizes))
    assignment = np.zeros(len(sizes), dtype=int)
    loads = np.zeros(folds, dtype=int)
    for group in shuffled[np.argsort(-sizes[shuffled], kind="stable")]:
        fold = int(np.argmin(loads))
        assignment[group] = fold
        loads[fold] += sizes[group]
    return assignment[inverse]


class RidgePath:
    """Ridge fitted once through an SVD, so every alpha costs only a matrix product."""

    def __init__(self, x: np.ndarray, y: np.ndarray) -> None:
        self.mean = x.mean(axis=0)
        scale = x.std(axis=0)
        self.scale = np.where(scale > 0, scale, 1.0)
        self.intercept = y.mean(axis=0)
        u, self.singular, self.vt = np.linalg.svd((x - self.mean) / self.scale, full_matrices=False)
        self.projected = u.T @ (y - self.intercept)

    def predict(self, x: np.ndarray, alpha: float) -> np.ndarray:
        shrink = self.singular / (self.singular**2 + alpha)
        rotated = ((x - self.mean) / self.scale) @ self.vt.T
        return rotated @ (shrink[:, None] * self.projected) + self.intercept


def choose_alphas(
    x: np.ndarray, y: np.ndarray, groups: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    """The best alpha per dimension, using only the clips it's given."""

    assignment = group_folds(groups, INNER_FOLDS, rng)
    errors = np.zeros((len(ALPHAS), y.shape[1]))
    for fold in range(INNER_FOLDS):
        test = assignment == fold
        path = RidgePath(x[~test], y[~test])
        for index, alpha in enumerate(ALPHAS):
            errors[index] += ((path.predict(x[test], alpha) - y[test]) ** 2).sum(axis=0)
    return ALPHAS[errors.argmin(axis=0)]


def _predict(path: RidgePath, x: np.ndarray, alphas: np.ndarray) -> np.ndarray:
    columns = [path.predict(x, alpha)[:, d] for d, alpha in enumerate(alphas)]
    return np.stack(columns, axis=1)


def cross_validate(
    x: np.ndarray, y: np.ndarray, groups: np.ndarray, folds: int, repeats: int, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """Held-out predictions and mean-only baselines, each shaped (repeats, clips, dimensions)."""

    rng = np.random.default_rng(seed)
    predictions = np.zeros((repeats, *y.shape))
    baseline = np.zeros((repeats, *y.shape))
    for repeat in range(repeats):
        assignment = group_folds(groups, folds, rng)
        for fold in range(folds):
            test = assignment == fold
            alphas = choose_alphas(x[~test], y[~test], groups[~test], rng)
            predictions[repeat, test] = _predict(RidgePath(x[~test], y[~test]), x[test], alphas)
            baseline[repeat, test] = y[~test].mean(axis=0)
    return predictions, baseline


def r_squared(y: np.ndarray, predictions: np.ndarray) -> np.ndarray:
    """R² per repeat and dimension, for predictions shaped (repeats, clips, dimensions)."""

    residual = ((predictions - y) ** 2).sum(axis=1)
    return 1 - residual / ((y - y.mean(axis=0)) ** 2).sum(axis=0)


def compare(
    first: np.ndarray,
    second: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    seed: int,
    bootstraps: int = BOOTSTRAPS,
) -> dict:
    """Mean R² difference, first minus second, with a 95% interval from resampling groups."""

    rng = np.random.default_rng(seed)
    labels = np.unique(groups)
    members = [np.flatnonzero(groups == label) for label in labels]
    differences = np.zeros(bootstraps)
    for sample in range(bootstraps):
        picked = rng.integers(len(members), size=len(members))
        clips = np.concatenate([members[index] for index in picked])
        sampled = y[clips]
        total = ((sampled - sampled.mean(axis=0)) ** 2).sum(axis=0)
        gap = ((second[:, clips] - sampled) ** 2).sum(axis=1) - (
            (first[:, clips] - sampled) ** 2
        ).sum(axis=1)
        differences[sample] = (gap / total).mean()
    low, high = np.percentile(differences, [2.5, 97.5])
    observed = float(r_squared(y, first).mean() - r_squared(y, second).mean())
    ahead = "first" if low > 0 else "second" if high < 0 else None
    return {"difference": observed, "ci_low": float(low), "ci_high": float(high), "ahead": ahead}


def _vectors(table, model: str) -> dict[str, np.ndarray]:
    rows = table.filter(table.column("model").to_numpy(zero_copy_only=False) == model)
    hashes = rows.column("sha256").to_pylist()
    return dict(zip(hashes, np.asarray(rows.column("vector").to_pylist(), float), strict=True))


def _requested(record: dict, models: list[str] | None) -> list[str]:
    available = [name for name, model in record["models"].items() if model.get("status") == "ok"]
    for name in models or []:
        if name not in available:
            raise MoodError(f"model {name} is not in run {record['run_id']}")
    return models or available


def _matrices(
    vectors: dict[str, np.ndarray], labels: dict, hashes: list[str]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.stack([vectors[sha] for sha in hashes])
    y = np.array([labels[sha][:2] for sha in hashes])
    return x, y, np.array([labels[sha][2] for sha in hashes])


def _load(run_dir: Path) -> tuple[dict, object]:
    if not (run_dir / RUN_JSON).is_file():
        raise MoodError(f"{run_dir} is not a run directory")
    return load_run(run_dir)


def mood_probe(
    run_dir: Path,
    labels_path: Path,
    models: list[str] | None = None,
    *,
    folds: int = FOLDS,
    repeats: int = REPEATS,
    seed: int = 0,
) -> dict:
    """Score each model on the clips they all share, and write mood.json into the run."""

    record, table = _load(run_dir)
    names = _requested(record, models)
    labels = read_mood_labels(labels_path)
    vectors = {name: _vectors(table, name) for name in names}
    minimum = folds * MIN_CLIPS_PER_FOLD
    matched = {name: labels.keys() & vectors[name].keys() for name in names}
    usable = [name for name in names if len(matched[name]) >= minimum]
    shared = sorted(set.intersection(*(matched[n] for n in usable))) if usable else []

    report = {
        "run_id": record["run_id"],
        "labels_sha256": hashlib.sha256(labels_path.read_bytes()).hexdigest(),
        "labelled_clips": len(labels),
        "clips": len(shared),
        "unmatched_labels": len(labels) - len(shared),
        "seed": seed,
        "folds": folds,
        "repeats": repeats,
        "models": {},
        "comparisons": [],
    }
    held_out = {}
    for name in names:
        if name not in usable or len(shared) < minimum:
            report["models"][name] = {
                "status": "unavailable",
                "clips": len(matched[name]),
                "reason": f"needs at least {minimum} labelled clips",
            }
            continue
        x, y, groups = _matrices(vectors[name], labels, shared)
        held_out[name], baseline = cross_validate(x, y, groups, folds, repeats, seed)
        scores = r_squared(y, held_out[name])
        floor = r_squared(y, baseline)
        report["models"][name] = {
            "status": "ok",
            "revision": record["models"][name].get("revision"),
            "mean_r2": float(scores.mean()),
            **{
                dimension: {
                    "r2_mean": float(scores[:, d].mean()),
                    "r2_std": float(scores[:, d].std()),
                    "baseline_r2": float(floor[:, d].mean()),
                }
                for d, dimension in enumerate(DIMENSIONS)
            },
        }
    if held_out:
        _, y, groups = _matrices(vectors[next(iter(held_out))], labels, shared)
        for first, second in combinations(held_out, 2):
            result = compare(held_out[first], held_out[second], y, groups, seed)
            leader = {"first": first, "second": second, None: None}[result["ahead"]]
            report["comparisons"].append(
                {"first": first, "second": second, **result, "ahead": leader}
            )
    (run_dir / MOOD_JSON).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def predict_run(
    run_dir: Path,
    labels_path: Path,
    target_dir: Path,
    out: Path,
    models: list[str] | None = None,
    *,
    manifest: Path | None = None,
    seed: int = 0,
) -> int:
    """Fit on every labelled clip, then write predictions for another run's assets."""

    ensure_outside_repo(out)
    record, table = _load(run_dir)
    target_record, target_table = _load(target_dir)
    names = _requested(record, models)
    for name in names:
        ours = record["models"][name].get("revision")
        theirs = target_record["models"].get(name, {}).get("revision")
        if ours != theirs:
            raise MoodError(f"{name} used revision {ours} here but {theirs} in the other run")
    labels = read_mood_labels(labels_path)
    titles = {a.sha256: (a.artist, a.title) for a in read_manifest(manifest)} if manifest else {}

    rows = []
    for name in names:
        vectors = _vectors(table, name)
        hashes = sorted(labels.keys() & vectors.keys())
        if len(hashes) < FOLDS * MIN_CLIPS_PER_FOLD:
            raise MoodError(f"{name} has only {len(hashes)} labelled clips")
        x, y, groups = _matrices(vectors, labels, hashes)
        alphas = choose_alphas(x, y, groups, np.random.default_rng(seed))
        path = RidgePath(x, y)
        target = _vectors(target_table, name)
        predicted = _predict(path, np.stack(list(target.values())), alphas)
        for sha, (valence, arousal) in zip(target, predicted, strict=True):
            artist, title = titles.get(sha, ("", ""))
            rows.append(
                {
                    "sha256": sha,
                    "artist": artist,
                    "title": title,
                    "model": name,
                    "valence": round(float(valence), 4),
                    "arousal": round(float(arousal), 4),
                }
            )
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, PREDICTION_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
