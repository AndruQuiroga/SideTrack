"""Feature extraction stage."""

from __future__ import annotations

import logging
import time

import numpy as np

from .dsp import melspectrogram
from .io import _resources

try:  # pragma: no cover - optional dependency
    import librosa  # type: ignore
except Exception:  # pragma: no cover - librosa is optional
    librosa = None  # type: ignore


logger = logging.getLogger(__name__)


def extract_features(track_id: int, y: np.ndarray, sr: int, cache_dir) -> dict:
    if librosa is None:
        raise ImportError(
            "librosa is required for feature extraction; install sidetrack[extraction]"
        )

    start = time.perf_counter()
    mel = melspectrogram(track_id, y, sr, cache_dir)
    rms = librosa.feature.rms(S=mel)[0]
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    duration = time.perf_counter() - start
    logger.info(
        "extract_features track_id=%s duration=%.3fs cache_hit=%s resources=%s",
        track_id,
        duration,
        None,
        _resources(),
    )
    return {"bpm": float(tempo), "pumpiness": float(rms.mean())}
