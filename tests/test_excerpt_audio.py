import numpy as np
import pytest

from sidetrack.extraction import dsp

pytestmark = pytest.mark.unit


def test_excerpt_audio_centers_on_loudest_region():
    sr = 44100
    y = np.zeros(sr * 5, dtype=np.float32)
    y[2 * sr : 3 * sr] = 1.0  # loud section in the middle
    out = dsp.excerpt_audio(y, sr, 1.0)
    assert out.shape[-1] == sr
    # Loud section should dominate the excerpt
    assert out.mean() > 0.5
