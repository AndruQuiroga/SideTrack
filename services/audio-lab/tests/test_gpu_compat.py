"""Spec: analysis/audio-benchmark: GPU compatibility is checked before a model loads; runs
record it. torch is replaced by a stub, so these run without a GPU or the models extra."""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import numpy as np
import pyarrow.parquet as pq
import pytest
from conftest import HashAdapter

from audio_lab.adapters import ModelUnavailable
from audio_lab.adapters.torch_base import TorchAdapter, check_arch
from audio_lab.runs import EMBEDDINGS, RUN_JSON, embed_run, environment

PASCAL = (6, 1)
CU128 = ["sm_75", "sm_80", "sm_86", "sm_90", "sm_100", "sm_120"]


def fake_torch(capability=PASCAL, arch_list=CU128):
    """Test double for the parts of torch the check and the run environment read."""

    cuda = SimpleNamespace(
        is_available=lambda: True,
        get_device_capability=lambda index=0: capability,
        get_arch_list=lambda: list(arch_list),
        get_device_name=lambda index=0: "Stub GTX 1070 Ti",
        empty_cache=lambda: None,
    )
    return SimpleNamespace(
        __version__="2.11.0+stub",
        version=SimpleNamespace(cuda="12.x"),
        cuda=cuda,
        device=lambda spec: SimpleNamespace(index=None if spec == "cuda" else int(spec[5:])),
    )


class StubTorchAdapter(TorchAdapter):
    """Test double: never loads weights; optionally fails its probe like a missing kernel."""

    name = "stub-torch"
    checkpoint = "tests/stub"
    revision = "test"
    license = "test-only"
    pooling = "none"
    sample_rate = 8000
    expected_dim = 4

    def __init__(self, probe_error: Exception | None = None) -> None:
        super().__init__()
        self.probe_error = probe_error
        self.loaded = False

    def _load_model(self) -> None:
        self.loaded = True

    def _forward(self, batch):
        raise AssertionError("embed_windows is overridden")

    def embed_windows(self, batch: list[np.ndarray]) -> np.ndarray:
        if self.probe_error:
            raise self.probe_error
        return np.zeros((len(batch), self.expected_dim), dtype=np.float32) + 1.0


@pytest.fixture()
def stub_torch(monkeypatch):
    def install(**kwargs):
        torch = fake_torch(**kwargs)
        monkeypatch.setitem(sys.modules, "torch", torch)
        return torch

    return install


@pytest.mark.parametrize(
    ("capability", "arch_list"),
    [
        (PASCAL, ["sm_50", "sm_60", "sm_70"]),  # sm_60 cubins run on 6.1
        (PASCAL, ["sm_61"]),
        (PASCAL, ["sm_90", "compute_60"]),  # PTX JIT-compiles on newer GPUs
        ((12, 0), CU128),
    ],
)
def test_compatible_builds_pass(capability, arch_list):
    check_arch(fake_torch(capability, arch_list), "cuda")


@pytest.mark.parametrize(
    ("capability", "arch_list"),
    [
        (PASCAL, CU128),
        (PASCAL, ["sm_62"]),  # a newer minor's cubin doesn't run on 6.1
        (PASCAL, ["compute_70"]),  # PTX only runs on its own version and newer
    ],
)
def test_incompatible_builds_name_the_gpu_and_the_build(capability, arch_list):
    with pytest.raises(ModelUnavailable) as caught:
        check_arch(fake_torch(capability, arch_list), "cuda:0")
    message = str(caught.value)
    assert f"sm_{capability[0]}{capability[1]}" in message
    assert all(arch in message for arch in arch_list)


def test_torch_build_without_sm61_marks_every_model_unavailable(
    stub_torch, make_manifest, audio_dir, tmp_path
):
    stub_torch()
    adapters = [StubTorchAdapter(), StubTorchAdapter()]
    adapters[1].name = "stub-torch-2"
    manifest = make_manifest([("A", "One", "full", 12, 220)])

    run = embed_run(manifest, audio_dir, adapters, tmp_path / "runs", device="cuda", commit="t")

    record = json.loads((run.path / RUN_JSON).read_text(encoding="utf-8"))
    for name in ("stub-torch", "stub-torch-2"):
        assert record["models"][name]["status"] == "unavailable"
        assert "sm_61" in record["models"][name]["reason"]
        assert "sm_120" in record["models"][name]["reason"]
    assert not any(a.loaded for a in adapters)
    assert pq.read_table(run.path / EMBEDDINGS).num_rows == 0


def test_cuda_error_in_the_probe_is_unavailable_and_the_run_continues(
    stub_torch, make_manifest, audio_dir, tmp_path
):
    stub_torch(arch_list=["sm_61"])
    broken = StubTorchAdapter(RuntimeError("CUDA error: no kernel image is available"))
    manifest = make_manifest([("A", "One", "full", 12, 220)])

    run = embed_run(
        manifest, audio_dir, [broken, HashAdapter()], tmp_path / "runs", device="cuda", commit="t"
    )

    record = json.loads((run.path / RUN_JSON).read_text(encoding="utf-8"))
    assert record["models"]["stub-torch"]["status"] == "unavailable"
    assert "no kernel image" in record["models"]["stub-torch"]["reason"]
    assert record["models"]["hash"]["status"] == "ok"
    assert pq.read_table(run.path / EMBEDDINGS).column("model").to_pylist() == ["hash"]


def test_environment_records_capability_and_arch_list(stub_torch, monkeypatch):
    stub_torch(arch_list=["sm_60", "sm_61"])
    monkeypatch.setattr("audio_lab.runs.shutil.which", lambda name: None)  # no nvidia-smi

    env = environment()

    assert env["compute_capability"] == "6.1"
    assert env["arch_list"] == ["sm_60", "sm_61"]
