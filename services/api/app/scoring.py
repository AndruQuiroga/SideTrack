from __future__ import annotations

import hashlib
import math
import random

from sqlalchemy.orm import Session
from sqlalchemy import select

from .models import Embedding, Feature
from .constants import AXES, SUPPORTED_METHODS


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _score_zero_shot(vector: list[float], axis: str) -> float:
    if not vector:
        raise ValueError("empty embedding vector")
    dim = len(vector)
    # generate deterministic weights based on axis name
    h = hashlib.sha256(axis.encode()).digest()
    rnd = random.Random(h)
    weights = [rnd.uniform(-1.0, 1.0) for _ in range(dim)]
    score = sum(v * w for v, w in zip(vector, weights)) / dim
    return float(round(_sigmoid(score), 6))


def _score_supervised(feat: Feature, axis: str) -> float:
    # very naive implementation: average a few numeric features
    values = [
        feat.bpm or 0.0,
        feat.pumpiness or 0.0,
        feat.percussive_harmonic_ratio or 0.0,
    ]
    if not any(values):
        raise ValueError("insufficient features")
    mean = sum(values) / len(values)
    # normalize assuming typical range 0-200
    score = max(0.0, min(1.0, mean / 200.0))
    return float(round(score, 6))


def score_axes(db: Session, track_id: int, method: str = "zero") -> dict[str, float]:
    if method not in SUPPORTED_METHODS:
        raise ValueError("unknown method")

    if method == "zero":
        emb = db.execute(select(Embedding).where(Embedding.track_id == track_id)).scalar_one_or_none()
        if not emb or not emb.vector:
            raise ValueError("embedding not found")
        return {ax: _score_zero_shot(emb.vector, ax) for ax in AXES}

    # supervised
    feat = db.execute(select(Feature).where(Feature.track_id == track_id)).scalar_one_or_none()
    if not feat:
        raise ValueError("features not found")
    return {ax: _score_supervised(feat, ax) for ax in AXES}
