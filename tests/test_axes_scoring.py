import pytest

from sidetrack.scoring import compute_axes


def test_compute_axes_golden():
    features = {"bpm": 120.0, "pumpiness": 0.5}
    embeddings = {"test": [0.1, 0.2, 0.3]}
    scores = compute_axes(features, embeddings, model="test")
    assert scores == pytest.approx(
        {
            "energy": 0.5,
            "danceability": 0.6,
            "valence": 0.1,
            "acousticness": 0.2,
        }
    )
