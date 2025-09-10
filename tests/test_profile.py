from datetime import datetime, timedelta

import pytest

from sidetrack.profile import compute_recent_profile, compute_discovery, rerank_vector


def test_compute_recent_profile_medians():
    tracks = [
        {"tempo": 120, "valence": 0.5, "energy": 0.8},
        {"tempo": 128, "valence": 0.7, "energy": 0.6},
        {"tempo": 110, "valence": 0.3, "energy": 0.9},
    ]
    profile = compute_recent_profile(tracks)
    assert profile == pytest.approx({"tempo": 120, "valence": 0.5, "energy": 0.8})


def test_compute_discovery_percentages():
    now = datetime(2023, 2, 1)
    history = [
        {"played_at": now - timedelta(days=40), "artist": "A", "label": "L1"},
        {"played_at": now - timedelta(days=10), "artist": "B", "label": "L2"},
        {"played_at": now - timedelta(days=5), "artist": "A", "label": "L3"},
        {"played_at": now - timedelta(days=3), "artist": "C", "label": "L2"},
    ]
    discovery = compute_discovery(history, now=now)
    assert discovery == pytest.approx({"new_artist_pct": 66.6667, "new_label_pct": 100.0})


def test_rerank_vector_golden():
    profile = {"tempo": 120, "valence": 0.5, "energy": 0.8}
    candidate = {
        "cf_score": 0.7,
        "artist": "D",
        "label": "L2",
        "tempo": 125,
        "valence": 0.6,
        "energy": 0.75,
    }
    vector = rerank_vector(
        candidate, profile, known_artists={"A", "B", "C"}, known_labels={"L1", "L2", "L3"}
    )
    assert vector == pytest.approx([0.7, 1.0, 0.0, 0.1666319])
