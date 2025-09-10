from __future__ import annotations

"""Feature extraction stage."""

import numpy as np
import librosa

from .dsp import melspectrogram


def extract_features(track_id: int, y: np.ndarray, sr: int, cache_dir) -> dict:
    mel = melspectrogram(track_id, y, sr, cache_dir)
    rms = librosa.feature.rms(S=mel)[0]
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return {"bpm": float(tempo), "pumpiness": float(rms.mean())}
