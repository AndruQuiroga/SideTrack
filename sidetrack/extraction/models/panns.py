from __future__ import annotations

import numpy as np


def embed(y: np.ndarray, sr: int, device: str = "cpu") -> np.ndarray:
    return np.array([float(len(y)), float(sr)], dtype=float)
