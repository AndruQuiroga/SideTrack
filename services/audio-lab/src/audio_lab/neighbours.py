"""Nearest neighbours and self-retrieval, computed within one model only (ADR 0004)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pyarrow as pa

from .manifest import Asset

TOP_K = 10


@dataclass(frozen=True)
class Neighbour:
    seed: str
    sha256: str
    score: float


@dataclass(frozen=True)
class Retrieval:
    seeds: int
    recall_at_1: float
    recall_at_10: float


def vectors_by_model(table: pa.Table) -> dict[str, dict[str, np.ndarray]]:
    """model → sha256 → unit vector. Each model's space stays separate."""

    out: dict[str, dict[str, np.ndarray]] = {}
    for model, sha, vector in zip(
        table.column("model").to_pylist(),
        table.column("sha256").to_pylist(),
        table.column("vector").to_pylist(),
        strict=True,
    ):
        out.setdefault(model, {})[sha] = np.asarray(vector, dtype=np.float32)
    return out


def _pool(assets: list[Asset], vectors: dict[str, np.ndarray]) -> tuple[list[Asset], np.ndarray]:
    """Full-track assets that this model embedded: the neighbour candidates."""

    full = [a for a in assets if a.kind == "full" and a.sha256 in vectors]
    if not full:
        return [], np.zeros((0, 0), dtype=np.float32)
    return full, np.stack([vectors[a.sha256] for a in full])


def _query(seed_assets: list[Asset], vectors: dict[str, np.ndarray]) -> np.ndarray | None:
    for kind in ("full", "preview"):
        for asset in seed_assets:
            if asset.kind == kind and asset.sha256 in vectors:
                return vectors[asset.sha256]
    return None


def neighbours(
    assets: list[Asset], vectors: dict[str, np.ndarray], k: int = TOP_K
) -> dict[str, list[Neighbour]]:
    """Seed → top-k full tracks of *other* seeds by cosine similarity, for one model."""

    by_seed: dict[str, list[Asset]] = {}
    for asset in assets:
        by_seed.setdefault(asset.seed, []).append(asset)
    pool, matrix = _pool(assets, vectors)
    result: dict[str, list[Neighbour]] = {}
    for seed, seed_assets in by_seed.items():
        query = _query(seed_assets, vectors)
        if query is None or not pool:
            continue
        scores = matrix @ query
        ranked = [i for i in np.argsort(-scores) if pool[i].seed != seed][:k]
        result[seed] = [Neighbour(pool[i].seed, pool[i].sha256, float(scores[i])) for i in ranked]
    return result


def self_retrieval(assets: list[Asset], vectors: dict[str, np.ndarray]) -> Retrieval:
    """How often a seed's preview finds its own full track among all full tracks."""

    pool, matrix = _pool(assets, vectors)
    seeds_with_full = {a.seed for a in pool}
    hits1 = hits10 = total = 0
    for preview in (a for a in assets if a.kind == "preview" and a.sha256 in vectors):
        if preview.seed not in seeds_with_full:
            continue
        order = np.argsort(-(matrix @ vectors[preview.sha256]))
        rank = next(r for r, i in enumerate(order) if pool[i].seed == preview.seed)
        total += 1
        hits1 += rank == 0
        hits10 += rank < 10
    if total == 0:
        return Retrieval(0, 0.0, 0.0)
    return Retrieval(total, hits1 / total, hits10 / total)
