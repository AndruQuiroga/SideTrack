"""One model's vectors in two runs, compared per asset (e.g. RTX 5070 against GTX 1070 Ti).

This compares a model with itself across hardware, never two models (ADR 0004).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from .neighbours import vectors_by_model
from .runs import EMBEDDINGS, RUN_JSON

WINDOW_KEYS = ("window_s", "min_tail_s", "max_full_s")


class ParityError(Exception):
    """The runs can't be compared for this model."""


def _load(run_dir: Path, model: str) -> tuple[dict, dict[str, np.ndarray]]:
    if not (run_dir / RUN_JSON).is_file():
        raise ParityError(f"{run_dir} is not a run directory (no {RUN_JSON})")
    record = json.loads((run_dir / RUN_JSON).read_text(encoding="utf-8"))
    vectors = vectors_by_model(pq.read_table(run_dir / EMBEDDINGS)).get(model, {})
    result = record["models"].get(model, {})
    if result.get("status") != "ok" or not vectors:
        raise ParityError(f"run {record['run_id']} has no {model} embeddings")
    return record, vectors


def parity(run_a: Path, run_b: Path, model: str, threshold: float = 0.999) -> dict:
    record_a, vectors_a = _load(run_a, model)
    record_b, vectors_b = _load(run_b, model)
    ids = record_a["run_id"], record_b["run_id"]

    revisions = record_a["models"][model]["revision"], record_b["models"][model]["revision"]
    if revisions[0] != revisions[1]:
        raise ParityError(
            f"{model} revisions differ: {revisions[0]} in {ids[0]}, {revisions[1]} in {ids[1]}"
        )
    windows = [{k: r["windows"].get(k) for k in WINDOW_KEYS} for r in (record_a, record_b)]
    if windows[0] != windows[1]:
        raise ParityError(
            f"window settings differ: {windows[0]} in {ids[0]}, {windows[1]} in {ids[1]}"
        )

    shared = sorted(vectors_a.keys() & vectors_b.keys())
    if not shared:
        raise ParityError(f"runs {ids[0]} and {ids[1]} share no {model} assets")
    a = np.stack([vectors_a[sha] for sha in shared]).astype(np.float64)
    b = np.stack([vectors_b[sha] for sha in shared]).astype(np.float64)
    cosine = (a * b).sum(axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))
    below = sorted(
        ((sha, float(c)) for sha, c in zip(shared, cosine, strict=True) if c < threshold),
        key=lambda item: item[1],
    )
    return {
        "model": model,
        "runs": list(ids),
        "revision": revisions[0],
        "shared": len(shared),
        "only_in_a": len(vectors_a.keys() - vectors_b.keys()),
        "only_in_b": len(vectors_b.keys() - vectors_a.keys()),
        "min": float(cosine.min()),
        "p1": float(np.percentile(cosine, 1)),
        "median": float(np.median(cosine)),
        "threshold": threshold,
        "below": [{"sha256": sha, "cosine": c} for sha, c in below],
    }
