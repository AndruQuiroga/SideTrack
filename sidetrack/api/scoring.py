from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import Embedding, Feature

from .constants import AXES, SUPPORTED_METHODS

MODEL_DIR = Path(__file__).resolve().parent / "model_data"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _round6(x: float) -> float:
    return float(round(x, 6))


def method_version(method: str, version: str | None) -> str:
    """Return a method identifier including version."""
    return f"{method}_{version}" if version else method


# ---------------------------------------------------------------------------
# Zero-shot scoring (cosine prototype)
# ---------------------------------------------------------------------------


def _axis_prototype(axis: str, dim: int) -> list[float]:
    """Deterministically generate a prototype vector for an axis."""
    h = hashlib.sha256(axis.encode()).digest()
    rnd = random.Random(h)
    w = [rnd.uniform(-1.0, 1.0) for _ in range(dim)]
    # L2 normalise
    norm = math.sqrt(sum(v * v for v in w)) or 1.0
    return [v / norm for v in w]


def _score_zero_shot(vector: list[float], axis: str) -> tuple[float, float]:
    if not vector:
        raise ValueError("empty embedding vector")
    # normalise input embedding
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    v = [x / norm for x in vector]
    proto = _axis_prototype(axis, len(v))
    # cosine similarity in [-1, 1] mapped to [0, 1]
    cos = sum(a * b for a, b in zip(v, proto))
    val = _clamp01(0.5 * (cos + 1.0))
    # simple confidence from |cos|
    conf = _clamp01(abs(cos))
    return _round6(val), _round6(conf)


# ---------------------------------------------------------------------------
# Logistic regression scorer
# ---------------------------------------------------------------------------


@dataclass
class LogisticModel:
    bias: float
    weights: dict[str, float]

    @classmethod
    def from_dict(cls, data: dict) -> LogisticModel:
        return cls(bias=data.get("bias", 0.0), weights=data.get("weights", {}))

    def score(self, feat: Feature) -> tuple[float, float]:
        z = self.bias
        for name, w in self.weights.items():
            z += (getattr(feat, name) or 0.0) * w
        p = _sigmoid(z)
        conf = abs(p - 0.5) * 2
        return _round6(_clamp01(p)), _round6(_clamp01(conf))


_MODEL_CACHE: dict[tuple[str, str], dict[str, LogisticModel]] = {}


def _load_models(method: str, version: str) -> dict[str, LogisticModel]:
    key = (method, version)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]
    path = MODEL_DIR / f"{method}_{version}.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    models = {ax: LogisticModel.from_dict(cfg) for ax, cfg in data.items()}
    _MODEL_CACHE[key] = models
    return models


def clear_model_cache() -> None:
    _MODEL_CACHE.clear()


# ---------------------------------------------------------------------------
# Heuristic scorer from features
# ---------------------------------------------------------------------------


def _safe(d: dict | None, key: str, default: float = 0.0) -> float:
    if not isinstance(d, dict):
        return default
    try:
        v = d.get(key, default)
        return float(v)
    except Exception:
        return default


def _norm(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return _clamp01((x - lo) / (hi - lo))


def _score_heuristic(feat: Feature, axis: str) -> tuple[float, float]:
    # Use rough ranges for scaling; these can be tuned later.
    spectral = getattr(feat, "spectral", None) or {}
    dynamics = getattr(feat, "dynamics", None) or {}
    bpm = float(getattr(feat, "bpm", 0.0) or 0.0)
    pump = float(getattr(feat, "pumpiness", 0.0) or 0.0)
    phr = float(getattr(feat, "percussive_harmonic_ratio", 0.0) or 0.0)
    centroid = _safe(spectral, "centroid_mean", 0.0)
    dyn_range = _safe(dynamics, "dynamic_range", 0.0)

    if axis == "brightness":
        # spectral centroid 500..5000 Hz
        val = _norm(centroid, 500.0, 5000.0)
        conf = 0.7
    elif axis == "energy":
        # combine dynamic range, pumpiness and phr
        e1 = _norm(dyn_range, 0.0, 0.2)
        e2 = _clamp01(0.6 * _clamp01(pump) + 0.4 * _clamp01(phr))
        val = _clamp01(0.5 * e1 + 0.5 * e2)
        conf = 0.6
    elif axis == "danceability":
        # favor ~120 BPM; gaussian-like preference
        pref = math.exp(-((bpm - 120.0) ** 2) / (2 * 30.0**2))
        val = _clamp01(0.6 * pref + 0.4 * _clamp01(pump))
        conf = 0.6
    elif axis == "valence":
        # brighter + less dynamic contrast tends to sound "happier" heuristically
        b = _norm(centroid, 500.0, 5000.0)
        d = 1.0 - _norm(dyn_range, 0.0, 0.3)
        val = _clamp01(0.6 * b + 0.4 * d)
        conf = 0.5
    elif axis == "pumpiness":
        val = _clamp01(pump)
        conf = 0.7
    else:
        raise ValueError("unknown axis")

    return _round6(val), _round6(conf)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def score_axes(
    db: AsyncSession, track_id: int, method: str = "zero", version: str | None = None
) -> dict[str, dict[str, float]]:
    """Score a track across all axes using the specified method.

    Returns a mapping of axis -> {"value": float, "confidence": float}.
    """

    if method not in SUPPORTED_METHODS:
        raise ValueError("unknown method")

    if method == "zero":
        emb = (
            await db.execute(select(Embedding).where(Embedding.track_id == track_id))
        ).scalar_one_or_none()
        if not emb or not emb.vector:
            raise ValueError("embedding not found")
        return {
            ax: {"value": val, "confidence": conf}
            for ax, (val, conf) in {ax: _score_zero_shot(emb.vector, ax) for ax in AXES}.items()
        }

    # heuristic model from engineered features
    if method == "heur":
        feat = (
            await db.execute(select(Feature).where(Feature.track_id == track_id))
        ).scalar_one_or_none()
        if not feat:
            raise ValueError("features not found")
        out: dict[str, dict[str, float]] = {}
        for ax in AXES:
            val, conf = _score_heuristic(feat, ax)
            out[ax] = {"value": val, "confidence": conf}
        return out

    # logistic regression and other supervised models
    version = version or "v1"
    models = _load_models(method, version)
    feat = (
        await db.execute(select(Feature).where(Feature.track_id == track_id))
    ).scalar_one_or_none()
    if not feat:
        raise ValueError("features not found")
    scores: dict[str, dict[str, float]] = {}
    for ax in AXES:
        model = models.get(ax)
        if not model:
            raise ValueError(f"model for axis {ax} not found")
        val, conf = model.score(feat)
        scores[ax] = {"value": val, "confidence": conf}
    return scores
