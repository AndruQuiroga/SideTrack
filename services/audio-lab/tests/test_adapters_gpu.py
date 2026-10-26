"""Real models on the owner's GPU. Run with: uv run --extra models pytest -m gpu"""

from __future__ import annotations

import numpy as np
import pytest
from conftest import tone

from audio_lab.adapters import ADAPTERS, get_adapter, pool

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
