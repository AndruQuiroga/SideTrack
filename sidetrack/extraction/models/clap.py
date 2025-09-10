from __future__ import annotations

import numpy as np


def embed(y: np.ndarray, sr: int, device: str = "cpu") -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.standard_normal(4, dtype=float)
