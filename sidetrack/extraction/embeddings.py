from __future__ import annotations

"""Embedding computation using optional models."""

import json
import time
from importlib import import_module
from typing import Dict

import numpy as np
import structlog

from sidetrack.config.extraction import ExtractionConfig
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


logger = structlog.get_logger(__name__)


def compute_embeddings(track_id: int, y: np.ndarray, sr: int, cfg: ExtractionConfig, redis_conn=None) -> Dict[str, list[float]]:
    models: list[str] = []
    if cfg.embedding_model:
        models.extend([m.strip() for m in cfg.embedding_model.split(",") if m.strip()])
    if cfg.use_clap and "clap" not in models:
        models.append("clap")
    out: Dict[str, list[float]] = {}
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
            vec = emb.astype(float).tolist()
            if redis_conn is not None:
                redis_conn.set(key, json.dumps(vec))
        duration = time.perf_counter() - start
        logger.info(
            "extract_embedding",
            track_id=track_id,
            model=name,
            duration=duration,
            cache_hit=cache_hit,
            **_resources(),
        )
        out[name] = vec
    return out
