from __future__ import annotations

"""I/O utilities for the extraction pipeline."""

from pathlib import Path
from typing import Tuple

import numpy as np
import soundfile as sf

def cache_path(cache_dir: Path, track_id: int, kind: str, suffix: str) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{track_id}-{kind}.{suffix}"


def decode(track_id: int, path: str, cache_dir: Path) -> Tuple[np.ndarray, int]:
    """Decode ``path`` into a waveform, optionally caching the result."""

    cp = cache_path(cache_dir, track_id, "raw", "npz")
    if cp.exists():
        data = np.load(cp)
        y = data["y"]
        orig_sr = int(data["sr"])
    else:
        y, orig_sr = sf.read(path, always_2d=False)
        y = y.astype("float32")
        np.savez(cp, y=y, sr=orig_sr)
    return y, orig_sr


def load_melspec(track_id: int, cache_dir: Path) -> np.ndarray | None:
    cp = cache_path(cache_dir, track_id, "mel", "npy")
    if cp.exists():
        return np.load(cp)
    return None


def save_melspec(track_id: int, cache_dir: Path, mel: np.ndarray) -> None:
    cp = cache_path(cache_dir, track_id, "mel", "npy")
    np.save(cp, mel)
