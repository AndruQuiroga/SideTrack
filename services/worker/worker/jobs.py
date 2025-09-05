"""Background job implementations for the worker service."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

import numpy as np
import librosa
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("worker")

sys.path.append(str(Path(__file__).resolve().parents[2] / "api"))
from app.db import SessionLocal  # type: ignore
from app.models import Track, Feature  # type: ignore


def _basic_features(path: str) -> dict[str, float]:
    """Estimate a couple of simple audio features."""

    y, sr = librosa.load(path, sr=None, mono=True)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    pump = float(np.sqrt(np.mean(y ** 2)))
    return {"bpm": float(tempo), "pumpiness": pump}


def analyze_track(track_id: int) -> int:
    """Extract basic features for ``track_id`` and persist them.

    Parameters
    ----------
    track_id:
        Identifier of the track to analyze.

    Returns
    -------
    int
        The newly created features row id.
    """

    with SessionLocal() as db:
        track = db.get(Track, track_id)
        if not track or not track.path_local:
            raise ValueError("track missing")
        feats = _basic_features(track.path_local)
        feature = Feature(track_id=track_id, bpm=feats["bpm"], pumpiness=feats["pumpiness"])
        db.add(feature)
        db.commit()
        return feature.id


def compute_embeddings(data: List[float]) -> List[float]:
    """Compute a simple normalised embedding vector.

    Args:
        data: List of floats representing raw features.

    Returns:
        A list of floats normalised by the maximum value.
    """
    if not data:
        return []
    max_val = max(data)
    if max_val == 0:
        return [0 for _ in data]
    embeddings = [round(x / max_val, 4) for x in data]
    logger.info("computed embeddings")
    return embeddings
