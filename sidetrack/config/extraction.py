from __future__ import annotations

"""Configuration for the extraction pipeline."""

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:  # optional torch
    import torch
except Exception:  # pragma: no cover
    torch = None  # type: ignore


def _torch_device(spec: str) -> str:
    if spec == "auto":
        if torch is not None and torch.cuda.is_available():
            return "cuda"
        return "cpu"
    return spec if spec in {"cpu", "cuda"} else "cpu"


def _get_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, "1" if default else "0") in {"1", "true", "True"}


@dataclass
class ExtractionConfig:
    embedding_model: str | None = os.getenv("EMBEDDING_MODEL", "openl3")
    use_clap: bool = _get_bool("USE_CLAP", False)
    use_demucs: bool = _get_bool("USE_DEMUCS", False)
    excerpt_seconds: float | None = (
        float(os.getenv("EXCERPT_SECONDS", "0")) or None
    )
    torch_device: str = _torch_device(os.getenv("TORCH_DEVICE", "auto"))
    dataset_version: str = os.getenv("DATASET_VERSION", "v1")
    cache_dir: Path = Path(os.getenv("EXTRACTION_CACHE", "/tmp/sidetrack-cache"))

    def set_seed(self, seed: int = 0) -> None:
        import random

        random.seed(seed)
        np.random.seed(seed)
        if torch is not None:
            torch.manual_seed(seed)
