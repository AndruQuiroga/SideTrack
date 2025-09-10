from __future__ import annotations

"""Feature extraction stage."""

import time

import numpy as np
import librosa
import structlog

from .dsp import melspectrogram
from .io import _resources


logger = structlog.get_logger(__name__)


def extract_features(track_id: int, y: np.ndarray, sr: int, cache_dir) -> dict:
    start = time.perf_counter()
    mel = melspectrogram(track_id, y, sr, cache_dir)
    rms = librosa.feature.rms(S=mel)[0]
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    duration = time.perf_counter() - start
    logger.info(
        "extract_features", track_id=track_id, duration=duration, cache_hit=None, **_resources()
    )
    return {"bpm": float(tempo), "pumpiness": float(rms.mean())}
