"""Shared PyTorch plumbing. torch is imported only when a model loads (``models`` extra)."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

import numpy as np

from .base import Adapter, AdapterInfo, ModelUnavailable

INSTALL_HINT = "uv sync --project services/audio-lab --extra models"


def require(module: str) -> Any:
    try:
        return __import__(module)
    except ImportError as exc:
        raise ModelUnavailable(f"{module} is not installed ({INSTALL_HINT})") from exc


def compute_capability(torch: Any, device: str) -> tuple[int, int]:
    index = torch.device(device).index
    return tuple(torch.cuda.get_device_capability(0 if index is None else index))


def check_arch(torch: Any, device: str) -> None:
    """Refuse a GPU this torch build has no kernels for (CUDA 12.8 builds dropped Pascal).

    A cubin for sm_XY runs on X.Z when Z >= Y; PTX for compute_V JIT-compiles on V and newer.
    """

    major, minor = compute_capability(torch, device)
    built = list(torch.cuda.get_arch_list())
    for arch in built:
        kind, _, digits = arch.partition("_")
        if not digits.isdigit():
            continue
        m, n = int(digits[:-1]), int(digits[-1])
        if kind == "sm" and m == major and n <= minor:
            return
        if kind == "compute" and (m, n) <= (major, minor):
            return
    raise ModelUnavailable(
        f"torch {torch.__version__} has no kernels for this GPU (sm_{major}{minor}); "
        f"it was built for {', '.join(built) or 'no CUDA architectures'}"
    )


class TorchAdapter(Adapter):
    """fp32 inference; windows of equal length are batched together."""

    sample_rate: int
    expected_dim: int
    dtype = "float32"

    def __init__(self) -> None:
        self._torch: Any = None
        self._device = "cpu"
        self._model: Any = None

    def _prepare(self, device: str) -> Any:
        torch = require("torch")
        if device.startswith("cuda") and not torch.cuda.is_available():
            raise ModelUnavailable("CUDA is not available to PyTorch on this machine")
        if device.startswith("cuda"):
            check_arch(torch, device)
        self._torch, self._device = torch, device
        return torch

    @abstractmethod
    def _load_model(self) -> None:
        """Set ``self._model`` (and any processor); may adjust ``self.sample_rate``."""

    @abstractmethod
    def _forward(self, batch: list[np.ndarray]) -> Any:
        """Equal-length float32 windows → torch tensor (batch, dim)."""

    def load(self, device: str) -> AdapterInfo:
        self._prepare(device)
        try:
            self._load_model()
            probe = self.embed_windows([np.zeros(self.sample_rate, dtype=np.float32)])
        except ModelUnavailable:
            self.unload()
            raise
        except Exception as exc:  # download, checkpoint, remote-code or CUDA kernel failures
            self.unload()
            raise ModelUnavailable(f"could not load {self.checkpoint}: {exc}") from exc
        if probe.shape[1] != self.expected_dim:
            raise ModelUnavailable(
                f"{self.name} produced dim {probe.shape[1]}, declared {self.expected_dim}"
            )
        return AdapterInfo(
            self.name,
            self.checkpoint,
            self.revision,
            self.license,
            self.sample_rate,
            self.expected_dim,
            self.pooling,
            self.dtype,
        )

    def embed_windows(self, batch: list[np.ndarray]) -> np.ndarray:
        torch = self._torch
        out = np.zeros((len(batch), self.expected_dim), dtype=np.float32)
        groups: dict[int, list[int]] = {}
        for index, window in enumerate(batch):
            groups.setdefault(len(window), []).append(index)
        with torch.inference_mode():
            for indices in groups.values():
                vectors = self._forward([batch[i] for i in indices])
                out[indices] = vectors.float().cpu().numpy()
        return out

    def _tensor(self, batch: list[np.ndarray]) -> Any:
        return self._torch.from_numpy(np.stack(batch)).to(self._device)

    def unload(self) -> None:
        self._model = None
        if self._torch is not None and self._torch.cuda.is_available():
            self._torch.cuda.empty_cache()

    def reset_peak_memory(self) -> None:
        if self._torch is not None and self._device.startswith("cuda"):
            self._torch.cuda.reset_peak_memory_stats()

    def peak_memory_mib(self) -> float:
        if self._torch is not None and self._device.startswith("cuda"):
            return self._torch.cuda.max_memory_allocated() / 2**20
        return 0.0
