from __future__ import annotations

"""Embedding computation using optional models."""

import json
from importlib import import_module
from typing import Dict

import numpy as np

from sidetrack.config.extraction import ExtractionConfig


MODEL_MAP = {
    "openl3": "sidetrack.extraction.models.openl3",
    "musicnn": "sidetrack.extraction.models.musicnn",
    "clap": "sidetrack.extraction.models.clap",
    "panns": "sidetrack.extraction.models.panns",
}


def _embed_one(name: str, y: np.ndarray, sr: int, device: str) -> np.ndarray:
    mod = import_module(MODEL_MAP[name])
    return mod.embed(y, sr, device=device)


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
        if redis_conn is not None:
            val = redis_conn.get(key)
            if val is not None:
                vec = json.loads(val)
        if vec is None:
            emb = _embed_one(name, y, sr, cfg.torch_device)
            vec = emb.astype(float).tolist()
            if redis_conn is not None:
                redis_conn.set(key, json.dumps(vec))
        out[name] = vec
    return out
