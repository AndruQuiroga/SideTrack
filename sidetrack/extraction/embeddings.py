"""Embedding computation using optional models."""

from __future__ import annotations

import json
import logging
import time
from importlib import import_module

import numpy as np

from sidetrack.config import ExtractionConfig

from .io import _resources

MODEL_MAP = {
    "openl3": "sidetrack.extraction.models.openl3",
    "musicnn": "sidetrack.extraction.models.musicnn",
    "clap": "sidetrack.extraction.models.clap",
    "panns": "sidetrack.extraction.models.panns",
}


def _embed_one(name: str, y: np.ndarray, sr: int, device: str) -> np.ndarray:
    mod = import_module(MODEL_MAP[name])
    return mod.embed(y, sr, device=device)


logger = logging.getLogger(__name__)


def _normalize(vec: np.ndarray) -> list[float]:
    """Return a list normalised by the maximum absolute value.

    Values are scaled to ``[-1, 1]`` while preserving sign.  The output is
    rounded to four decimal places to keep payloads small and stable for
    caching.
    """

    if vec.size == 0:
        return []
    max_val = float(np.max(np.abs(vec)))
    if max_val == 0.0:
        return [0.0 for _ in vec]
    return [float(np.round(x / max_val, 4)) for x in vec]


def compute_embeddings(
    track_id: int, y: np.ndarray, sr: int, cfg: ExtractionConfig, redis_conn=None
) -> dict[str, list[float]]:
    models: list[str] = []
    if cfg.embedding_model:
        models.extend([m.strip() for m in cfg.embedding_model.split(",") if m.strip()])
    if cfg.use_clap and "clap" not in models:
        models.append("clap")
    out: dict[str, list[float]] = {}
    for name in models:
        key = f"emb:{name}:{track_id}:{cfg.dataset_version}"
        vec = None
        cache_hit = False
        start = time.perf_counter()
        if redis_conn is not None:
            val = redis_conn.get(key)
            if val is not None:
                vec = json.loads(val)
                cache_hit = True
        if vec is None:
            emb = _embed_one(name, y, sr, cfg.torch_device)
            vec = _normalize(emb)
            if redis_conn is not None:
                redis_conn.set(key, json.dumps(vec))
        duration = time.perf_counter() - start
        logger.info(
            "extract_embedding track_id=%s model=%s duration=%.3fs cache_hit=%s resources=%s",
            track_id,
            name,
            duration,
            cache_hit,
            _resources(),
        )
        out[name] = vec
    return out
