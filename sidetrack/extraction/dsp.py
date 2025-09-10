from __future__ import annotations

"""Signal processing helpers for the extraction pipeline."""

from pathlib import Path

import numpy as np
import librosa

from .io import load_melspec, save_melspec


def resample_audio(y: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return y
    return librosa.resample(y, orig_sr=orig_sr, target_sr=target_sr)


def excerpt_audio(y: np.ndarray, sr: int, seconds: float | None) -> np.ndarray:
    if not seconds or seconds <= 0:
        return y
    n = int(seconds * sr)
    if y.shape[-1] <= n:
        return y
    start = (y.shape[-1] - n) // 2
    return y[start : start + n]


def melspectrogram(track_id: int, y: np.ndarray, sr: int, cache_dir: Path) -> np.ndarray:
    mel = load_melspec(track_id, cache_dir)
    if mel is not None:
        return mel
    mel = librosa.feature.melspectrogram(y=y, sr=sr)
    save_melspec(track_id, cache_dir, mel)
    return mel
