from __future__ import annotations

"""Feature extraction stage."""

import time

import numpy as np
import structlog

from .dsp import melspectrogram
from .io import _resources

try:  # pragma: no cover - optional dependency
    import librosa  # type: ignore
except Exception:  # pragma: no cover - librosa is optional
    librosa = None  # type: ignore


logger = structlog.get_logger(__name__)


def extract_features(track_id: int, y: np.ndarray, sr: int, cache_dir) -> dict:
    if librosa is None:
        raise ImportError("librosa is required for feature extraction; install sidetrack[extractor]")

    start = time.perf_counter()
    mel = melspectrogram(track_id, y, sr, cache_dir)
    rms = librosa.feature.rms(S=mel)[0]
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    duration = time.perf_counter() - start
    logger.info(
        "extract_features", track_id=track_id, duration=duration, cache_hit=None, **_resources()
    )
    return {"bpm": float(tempo), "pumpiness": float(rms.mean())}
