"""Spec: analysis/audio-embeddings: enabled models, the benchmark's pipeline, unavailable models."""

from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from sidetrack.analysis.embeddings import ModelNotEnabled, ModelUnavailable, enabled_model
from sidetrack.analysis.embeddings.audio import EmbeddingFailed, pool, windows
from sidetrack.analysis.embeddings.muq_mulan import MuQMuLan, check_arch

pytestmark = pytest.mark.unit

RATE = 24000


def test_only_muq_mulan_is_enabled():
    assert enabled_model("muq-mulan").dim == 512
    with pytest.raises(ModelNotEnabled, match="'muq' is not enabled; enabled: muq-mulan"):
        enabled_model("muq")


# Same expectations as services/audio-lab/tests/test_audio.py: the pipelines must agree.
@pytest.mark.parametrize(
    ("seconds", "max_s", "expected"),
    [
        (25.0, None, [10.0, 10.0, 5.0]),  # a 5 s tail is kept (minimum 3 s)
        (22.0, None, [10.0, 10.0]),  # a 2 s tail is dropped
        (2.0, None, [2.0]),  # shorter than the minimum tail: one short window
        (400.0, 180.0, [10.0] * 18),  # full tracks are capped at 180 s
    ],
)
def test_windows_match_the_benchmark(seconds, max_s, expected):
    wave = np.zeros(int(seconds * RATE), dtype=np.float32)
    chunks = windows(wave, RATE, max_s=max_s)
    assert [len(c) / RATE for c in chunks] == expected


def test_pool_is_the_unit_mean():
    vectors = np.array([[3.0, 0.0], [0.0, 4.0]], dtype=np.float32)
    pooled = pool(vectors)
    assert pooled == pytest.approx([0.6, 0.8])
    assert float(np.linalg.norm(pooled)) == pytest.approx(1.0)


def test_pool_refuses_a_zero_vector():
    with pytest.raises(EmbeddingFailed):
        pool(np.zeros((2, 4), dtype=np.float32))


def test_api_and_cpu_worker_import_without_numpy_or_torch():
    """The API image has neither; only the gpu job may need them."""

    code = (
        "import sys; sys.modules['numpy'] = None; sys.modules['torch'] = None; "
        "import sidetrack.analysis, sidetrack.job_runner, sidetrack.worker, sidetrack.api.main"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_model_unavailable_without_torch(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", None)  # import torch raises ImportError
    with pytest.raises(ModelUnavailable, match="torch is not installed"):
        MuQMuLan().load("cuda:0")


def fake_torch(*, cuda=True, capability=(6, 1), arch_list=("sm_60",)):
    """Test double for the parts of torch the load path reads."""

    return SimpleNamespace(
        __version__="2.11.0+stub",
        cuda=SimpleNamespace(
            is_available=lambda: cuda,
            get_device_capability=lambda index=0: capability,
            get_arch_list=lambda: list(arch_list),
        ),
        device=lambda spec: SimpleNamespace(index=None if spec == "cuda" else int(spec[5:])),
    )


def test_model_unavailable_without_cuda(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", fake_torch(cuda=False))
    with pytest.raises(ModelUnavailable, match="CUDA is not available"):
        MuQMuLan().load("cuda:0")


def test_model_unavailable_without_muq(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", fake_torch())
    monkeypatch.setitem(sys.modules, "muq", None)
    with pytest.raises(ModelUnavailable, match="muq is not installed"):
        MuQMuLan().load("cuda:0")


def test_torch_build_without_the_gpu_architecture():
    with pytest.raises(ModelUnavailable, match=r"sm_61.*sm_75, sm_120"):
        check_arch(fake_torch(arch_list=("sm_75", "sm_120")), "cuda:0")
    check_arch(fake_torch(arch_list=("sm_50", "sm_60", "sm_90")), "cuda:0")  # the cu126 build
