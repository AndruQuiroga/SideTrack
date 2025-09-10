import numpy as np
import pytest

from sidetrack.extraction import stems

pytestmark = pytest.mark.unit


def test_stems_fallback_without_gpu(tmp_path):
    y = np.zeros(44100, dtype=np.float32)
    stems_out, model = stems.separate(y, 44100, True, cache_dir=tmp_path)
    assert "mix" in stems_out
    assert model is None
