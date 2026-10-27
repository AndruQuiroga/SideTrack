"""Real models on the owner's GPU. Run with: uv run --extra models pytest -m gpu"""

from __future__ import annotations

import json

import numpy as np
import pytest
from conftest import tone

from audio_lab.adapters import ADAPTERS, get_adapter, pool
from audio_lab.runs import RUN_JSON, embed_run

pytestmark = pytest.mark.gpu


@pytest.fixture(scope="module")
def cuda():
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("no CUDA device")
    return "cuda"


@pytest.mark.parametrize("name", list(ADAPTERS))
def test_adapter_embeds_real_audio(name, cuda):
    adapter = get_adapter(name)
    info = adapter.load(cuda)
    try:
        rate = info.sample_rate
        clips = [tone(10.0, 220.0, rate), tone(10.0, 1760.0, rate) + tone(10.0, 97.0, rate)]
        adapter.reset_peak_memory()
        vectors = [pool(adapter.embed_windows([clip])) for clip in clips]
        peak = adapter.peak_memory_mib()
    finally:
        adapter.unload()

    assert info.dim == adapter.expected_dim
    for vector in vectors:
        assert vector.shape == (info.dim,)
        assert np.all(np.isfinite(vector))
        assert np.std(vector) > 0
    assert not np.allclose(vectors[0], vectors[1])
    assert peak > 0


def test_run_records_capability_and_load_time(cuda, make_manifest, audio_dir, tmp_path):
    torch = pytest.importorskip("torch")
    manifest = make_manifest([("A", "One", "full", 12, 220), ("B", "Two", "preview", 6, 440)])

    run = embed_run(manifest, audio_dir, [get_adapter("muq-mulan")], tmp_path / "runs", device=cuda)

    record = json.loads((run.path / RUN_JSON).read_text(encoding="utf-8"))
    major, minor = torch.cuda.get_device_capability(0)
    assert record["environment"]["compute_capability"] == f"{major}.{minor}"
    assert record["environment"]["arch_list"] == torch.cuda.get_arch_list()
    perf = record["models"]["muq-mulan"]["performance"]
    assert perf["load_seconds"] > 0 and perf["peak_vram_mib"] > 0
    assert perf["embedded"] == 2
