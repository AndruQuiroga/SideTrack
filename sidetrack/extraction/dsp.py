"""Signal processing helpers for the extraction pipeline."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np

from .io import _resources, load_melspec, save_melspec

try:  # pragma: no cover - optional dependency
    import librosa  # type: ignore
except Exception:  # pragma: no cover - librosa is optional
    librosa = None  # type: ignore


logger = logging.getLogger(__name__)


def resample_audio(y: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return y
    if librosa is None:
        raise ImportError("librosa is required for resampling; install sidetrack[extraction]")
    return librosa.resample(y, orig_sr=orig_sr, target_sr=target_sr)


def excerpt_audio(y: np.ndarray, sr: int, seconds: float | None) -> np.ndarray:
    """Return an excerpt of ``seconds`` centered on the loudest region.

    The loudest region is approximated by the frame with the maximum RMS
    energy.  If ``seconds`` is ``None`` or non-positive, the full signal is
    returned unchanged.
    """

    if not seconds or seconds <= 0:
        return y
    n = int(seconds * sr)
    if y.shape[-1] <= n:
        return y

    if librosa is None:
        raise ImportError("librosa is required for excerpting; install sidetrack[extraction]")

    # Compute frame-wise RMS energy and locate the frame with the maximum
    # value.  Use this frame's centre as the centre of the excerpt.
    hop = 512
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    idx = int(rms.argmax())
    centre = idx * hop
    start = max(0, centre - n // 2)
    end = start + n
    if end > y.shape[-1]:
        end = y.shape[-1]
        start = end - n
    return y[start:end]


def melspectrogram(track_id: int, y: np.ndarray, sr: int, cache_dir: Path) -> np.ndarray:
    if librosa is None:
        raise ImportError("librosa is required for spectrograms; install sidetrack[extraction]")

    start = time.perf_counter()
    mel = load_melspec(track_id, cache_dir)
    cache_hit = mel is not None
    if not cache_hit:
        mel = librosa.feature.melspectrogram(y=y, sr=sr)
        save_melspec(track_id, cache_dir, mel)
    duration = time.perf_counter() - start
    logger.info(
        "extract_melspectrogram track_id=%s duration=%.3fs cache_hit=%s resources=%s",
        track_id,
        duration,
        cache_hit,
        _resources(),
    )
    return mel
