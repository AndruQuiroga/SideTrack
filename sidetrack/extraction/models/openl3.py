from __future__ import annotations

"""Lightweight mock of OpenL3 embedding."""

import numpy as np


def embed(y: np.ndarray, sr: int, device: str = "cpu") -> np.ndarray:
    """Return a deterministic embedding based on mean and std."""
    mean = float(np.mean(y))
    std = float(np.std(y))
    return np.array([mean, std], dtype=float)
