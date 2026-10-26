"""Decode audio to mono float32 at a model's rate, and cut it into fixed windows."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile
import soxr

WINDOW_S = 10.0
MIN_TAIL_S = 3.0
MAX_FULL_S = 180.0


class DecodeError(Exception):
    pass


def _ffmpeg(path: Path, sample_rate: int) -> np.ndarray:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise DecodeError(f"{path.suffix} needs ffmpeg on PATH to decode")
    result = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(path),
            "-f",
            "f32le",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-",
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise DecodeError(f"ffmpeg could not decode {path.name}")
    return np.frombuffer(result.stdout, dtype=np.float32).copy()


def decode(path: Path, sample_rate: int) -> np.ndarray:
    """Mono float32 samples at ``sample_rate``. libsndfile first, ffmpeg for m4a/webm."""

    try:
        data, rate = soundfile.read(str(path), dtype="float32", always_2d=True)
    except (soundfile.LibsndfileError, RuntimeError, TypeError):
        wave = _ffmpeg(path, sample_rate)
    else:
        wave = data.mean(axis=1)
        if rate != sample_rate:
            wave = soxr.resample(wave, rate, sample_rate).astype(np.float32)
    if wave.size == 0:
        raise DecodeError(f"{path.name} decoded to no samples")
    return wave


def windows(
    wave: np.ndarray,
    sample_rate: int,
    *,
    window_s: float = WINDOW_S,
    min_tail_s: float = MIN_TAIL_S,
    max_s: float | None = None,
) -> list[np.ndarray]:
    """Non-overlapping windows; a final partial window is kept if at least ``min_tail_s``."""

    if max_s is not None:
        wave = wave[: int(max_s * sample_rate)]
    size = int(window_s * sample_rate)
    chunks = [wave[i : i + size] for i in range(0, len(wave), size)]
    kept = [c for c in chunks if len(c) == size or len(c) >= min_tail_s * sample_rate]
    if not kept and len(wave):
        kept = [wave]  # shorter than the minimum tail: one short window beats nothing
    return kept
