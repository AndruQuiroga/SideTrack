"""MuQ-MuLan on PyTorch, as benchmarked in services/audio-lab (fp32, MuLan audio projection).

torch and muq exist only in the GPU worker's environment (services/gpu-worker). Anything
missing is reported as unavailable; this module never produces a vector it didn't compute.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .registry import MUQ_MULAN, EmbeddingModel, ModelUnavailable

INSTALL_HINT = "run the GPU worker image (services/gpu-worker)"


def _require(module: str) -> Any:
    try:
        return __import__(module)
    except ImportError as exc:
        raise ModelUnavailable(f"{module} is not installed ({INSTALL_HINT})") from exc


def check_arch(torch: Any, device: str) -> None:
    """Refuse a GPU this torch build has no kernels for (CUDA 12.8+ builds dropped Pascal).

    A cubin for sm_XY runs on X.Z when Z >= Y; PTX for compute_V JIT-compiles on V and newer.
    """

    index = torch.device(device).index
    major, minor = torch.cuda.get_device_capability(0 if index is None else index)
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


class MuQMuLan:
    """Loads once per job; embeds equal-length windows in batches."""

    spec: EmbeddingModel = MUQ_MULAN

    def __init__(self) -> None:
        self._torch: Any = None
        self._model: Any = None
        self._device = "cpu"

    def load(self, device: str) -> None:
        torch = _require("torch")
        if device.startswith("cuda"):
            if not torch.cuda.is_available():
                raise ModelUnavailable("CUDA is not available to PyTorch on this machine")
            check_arch(torch, device)
        self._torch, self._device = torch, device
        muq = _require("muq")
        try:
            model = muq.MuQMuLan.from_pretrained(self.spec.checkpoint, revision=self.spec.revision)
            self._model = model.to(device).eval()
            probe = self.embed_windows([np.zeros(self.spec.sample_rate, dtype=np.float32)])
        except ModelUnavailable:
            raise
        except Exception as exc:  # download, checkpoint or CUDA kernel failures
            self._model = None
            raise ModelUnavailable(f"could not load {self.spec.checkpoint}: {exc}") from exc
        if probe.shape[1] != self.spec.dim:
            raise ModelUnavailable(
                f"{self.spec.name} produced dim {probe.shape[1]}, not {self.spec.dim}"
            )

    def embed_windows(self, batch: list[np.ndarray]) -> np.ndarray:
        """Shape (len(batch), dim); windows of equal length share one forward pass."""

        torch = self._torch
        out = np.zeros((len(batch), self.spec.dim), dtype=np.float32)
        groups: dict[int, list[int]] = {}
        for index, window in enumerate(batch):
            groups.setdefault(len(window), []).append(index)
        with torch.inference_mode():
            for indices in groups.values():
                stacked = torch.from_numpy(np.stack([batch[i] for i in indices])).to(self._device)
                vectors = self._model(wavs=stacked)
                out[indices] = vectors.float().cpu().numpy()
        return out
