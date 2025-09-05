from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from .constants import AXES, SUPPORTED_METHODS
from .models import Embedding, Feature


MODEL_DIR = Path(__file__).resolve().parent / "model_data"


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def method_version(method: str, version: str | None) -> str:
    """Return a method identifier including version."""
    return f"{method}_{version}" if version else method


# ---------------------------------------------------------------------------
# Zero shot scoring
# ---------------------------------------------------------------------------


def _score_zero_shot(vector: list[float], axis: str) -> Tuple[float, float]:
    if not vector:
        raise ValueError("empty embedding vector")
    dim = len(vector)
    h = hashlib.sha256(axis.encode()).digest()
    rnd = random.Random(h)
    weights = [rnd.uniform(-1.0, 1.0) for _ in range(dim)]
    score = sum(v * w for v, w in zip(vector, weights)) / dim
    val = float(round(_sigmoid(score), 6))
    conf = float(round(abs(val - 0.5) * 2, 6))
    return val, conf


# ---------------------------------------------------------------------------
# Logistic regression scorer
# ---------------------------------------------------------------------------


@dataclass
class LogisticModel:
    bias: float
    weights: Dict[str, float]

    @classmethod
    def from_dict(cls, data: dict) -> "LogisticModel":
        return cls(bias=data.get("bias", 0.0), weights=data.get("weights", {}))

    def score(self, feat: Feature) -> Tuple[float, float]:
        z = self.bias
        for name, w in self.weights.items():
            z += (getattr(feat, name) or 0.0) * w
        p = _sigmoid(z)
        conf = abs(p - 0.5) * 2
        return float(round(p, 6)), float(round(conf, 6))


_MODEL_CACHE: Dict[Tuple[str, str], Dict[str, LogisticModel]] = {}


def _load_models(method: str, version: str) -> Dict[str, LogisticModel]:
    key = (method, version)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]
    path = MODEL_DIR / f"{method}_{version}.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    models = {ax: LogisticModel.from_dict(cfg) for ax, cfg in data.items()}
    _MODEL_CACHE[key] = models
    return models


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_axes(
    db: Session, track_id: int, method: str = "zero", version: str | None = None
) -> Dict[str, Dict[str, float]]:
    """Score a track across all axes using the specified method.

    Returns a mapping of axis -> {"value": float, "confidence": float}.
    """

    if method not in SUPPORTED_METHODS:
        raise ValueError("unknown method")

    if method == "zero":
        emb = db.execute(select(Embedding).where(Embedding.track_id == track_id)).scalar_one_or_none()
        if not emb or not emb.vector:
            raise ValueError("embedding not found")
        return {ax: {"value": val, "confidence": conf} for ax, (val, conf) in {
            ax: _score_zero_shot(emb.vector, ax) for ax in AXES
        }.items()}

    # logistic regression and other supervised models
    version = version or "v1"
    models = _load_models(method, version)
    feat = db.execute(select(Feature).where(Feature.track_id == track_id)).scalar_one_or_none()
    if not feat:
        raise ValueError("features not found")
    scores: Dict[str, Dict[str, float]] = {}
    for ax in AXES:
        model = models.get(ax)
        if not model:
            raise ValueError(f"model for axis {ax} not found")
        val, conf = model.score(feat)
        scores[ax] = {"value": val, "confidence": conf}
    return scores

