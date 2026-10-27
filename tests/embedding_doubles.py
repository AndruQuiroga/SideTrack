"""Test doubles for audio embeddings. Never used outside tests (AGENTS.md: no fakes)."""

from __future__ import annotations

import hashlib

import numpy as np

from sidetrack.analysis.embeddings.registry import MUQ_MULAN, EmbeddingModel, ModelUnavailable


class HashEmbedder:
    """Hashes each window's samples into a MuQ-MuLan-sized vector; counts loads."""

    spec: EmbeddingModel = MUQ_MULAN

    def __init__(self) -> None:
        self.loads: list[str] = []
        self.windows_seen = 0

    def load(self, device: str) -> None:
        self.loads.append(device)

    def embed_windows(self, batch: list[np.ndarray]) -> np.ndarray:
        rows = []
        for window in batch:
            self.windows_seen += 1
            seed = int.from_bytes(hashlib.sha256(window.tobytes()).digest()[:4], "little")
            rows.append(np.random.default_rng(seed).standard_normal(self.spec.dim))
        return np.stack(rows).astype(np.float32)


class UnloadableEmbedder(HashEmbedder):
    def load(self, device: str) -> None:
        raise ModelUnavailable("CUDA is not available to PyTorch on this machine")
