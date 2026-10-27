"""The adapter contract (ADR 0004). An adapter that can't load says so; it never fakes vectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass

import numpy as np


class ModelUnavailable(Exception):
    """Weights, libraries or device are missing. The run records the reason."""


@dataclass(frozen=True)
class AdapterInfo:
    name: str
    checkpoint: str
    revision: str
    license: str
    sample_rate: int
    dim: int
    pooling: str
    dtype: str

    def as_dict(self) -> dict:
        return asdict(self)


class Adapter(ABC):
    """Loads one model and turns a batch of equal-rate windows into one vector per window."""

    name: str
    checkpoint: str
    revision: str
    license: str
    pooling: str
    max_full_s: float | None = None  # per-adapter override of the full-track cap

    @abstractmethod
    def load(self, device: str) -> AdapterInfo:
        """Load weights onto ``device``; raise ModelUnavailable with a reason."""

    @abstractmethod
    def embed_windows(self, batch: list[np.ndarray]) -> np.ndarray:
        """Return shape (len(batch), dim)."""

    def unload(self) -> None:  # noqa: B027 (optional hook)
        """Free model memory before the next adapter runs."""

    def reset_peak_memory(self) -> None:  # noqa: B027 (optional hook)
        """Start a fresh peak-memory measurement."""

    def peak_memory_mib(self) -> float:
        """Peak device memory since the last reset; 0.0 off-GPU."""
        return 0.0


def pool(vectors: np.ndarray) -> np.ndarray:
    """Mean over windows, then L2-normalise: one vector per asset."""

    mean = vectors.astype(np.float32).mean(axis=0)
    norm = float(np.linalg.norm(mean))
    if not np.isfinite(norm) or norm == 0.0:
        raise ValueError("embedding is zero or not finite")
    return mean / norm
