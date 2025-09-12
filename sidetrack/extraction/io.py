"""I/O utilities for the extraction pipeline."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np

try:  # pragma: no cover - optional dependency
    import soundfile as sf  # type: ignore
except Exception:  # pragma: no cover - soundfile is optional
    sf = None  # type: ignore

try:  # pragma: no cover - optional dependency
    import psutil  # type: ignore
except Exception:  # pragma: no cover - psutil not installed
    psutil = None  # type: ignore


logger = logging.getLogger(__name__)


def _resources() -> dict:
    """Return current CPU/GPU utilisation for logging."""
    cpu = psutil.cpu_percent() if psutil else None
    # GPU stats are environment specific; default to ``0`` when unavailable.
    return {"cpu": cpu, "gpu": 0.0}


def cache_path(cache_dir: Path, track_id: int, kind: str, suffix: str) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{track_id}-{kind}.{suffix}"


def decode(track_id: int, path: str, cache_dir: Path) -> tuple[np.ndarray, int]:
    """Decode ``path`` into a waveform, optionally caching the result."""

    if sf is None:
        raise ImportError("soundfile is required for audio decoding; install sidetrack[extractor]")

    start = time.perf_counter()
    cp = cache_path(cache_dir, track_id, "raw", "npz")
    cache_hit = cp.exists()
    if cache_hit:
        data = np.load(cp)
        y = data["y"]
        orig_sr = int(data["sr"])
    else:
        y, orig_sr = sf.read(path, always_2d=False)
        y = y.astype("float32")
        np.savez(cp, y=y, sr=orig_sr)
    duration = time.perf_counter() - start
    logger.info(
        "extract_decode track_id=%s duration=%.3fs cache_hit=%s resources=%s",
        track_id,
        duration,
        cache_hit,
        _resources(),
    )
    return y, orig_sr


def load_melspec(track_id: int, cache_dir: Path) -> np.ndarray | None:
    cp = cache_path(cache_dir, track_id, "mel", "npy")
    if cp.exists():
        return np.load(cp)
    return None


def save_melspec(track_id: int, cache_dir: Path, mel: np.ndarray) -> None:
    cp = cache_path(cache_dir, track_id, "mel", "npy")
    np.save(cp, mel)
