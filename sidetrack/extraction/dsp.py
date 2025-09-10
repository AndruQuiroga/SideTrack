from __future__ import annotations

"""Signal processing helpers for the extraction pipeline."""

from pathlib import Path
import time

import numpy as np
import librosa
import structlog

from .io import load_melspec, save_melspec
from .io import _resources


logger = structlog.get_logger(__name__)


def resample_audio(y: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return y
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
    start = time.perf_counter()
    mel = load_melspec(track_id, cache_dir)
    cache_hit = mel is not None
    if not cache_hit:
        mel = librosa.feature.melspectrogram(y=y, sr=sr)
        save_melspec(track_id, cache_dir, mel)
    duration = time.perf_counter() - start
    logger.info(
        "extract_melspectrogram",
        track_id=track_id,
        duration=duration,
        cache_hit=cache_hit,
        **_resources(),
    )
    return mel
