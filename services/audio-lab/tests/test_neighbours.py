"""Spec: neighbours are computed within one model; self-retrieval is measured."""

from __future__ import annotations

import numpy as np
import pyarrow as pa

from audio_lab.manifest import Asset
from audio_lab.neighbours import neighbours, self_retrieval, vectors_by_model


def _asset(sha: str, artist: str, kind: str = "full") -> Asset:
    return Asset(f"{sha}.wav", sha, kind, "test", sha, 10.0, "confirmed", None, artist, "Song")


def _unit(*values: float) -> np.ndarray:
    v = np.asarray(values, dtype=np.float32)
    return v / np.linalg.norm(v)


ASSETS = [
    _asset("a" * 64, "A"),
    _asset("b" * 64, "A", "preview"),
    _asset("c" * 64, "B"),
    _asset("d" * 64, "C"),
]
VECTORS = {
    "a" * 64: _unit(1, 0, 0),
    "b" * 64: _unit(0.99, 0.1, 0),
    "c" * 64: _unit(0.9, 0.4, 0),
    "d" * 64: _unit(0, 0, 1),
}


def test_own_preview_and_full_are_excluded():
    result = neighbours(ASSETS, VECTORS)
    seed_a = ASSETS[0].seed
    assert [n.seed for n in result[seed_a]] == [ASSETS[2].seed, ASSETS[3].seed]
    assert all(n.sha256 not in {"a" * 64, "b" * 64} for n in result[seed_a])


def test_neighbours_are_ranked_by_cosine():
    scores = [n.score for n in neighbours(ASSETS, VECTORS)[ASSETS[3].seed]]
    assert scores == sorted(scores, reverse=True)


def test_models_stay_separate():
    table = pa.table(
        {
            "model": ["muq", "muq", "clap"],
            "sha256": ["a" * 64, "c" * 64, "d" * 64],
            "vector": [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0, 0.0]],
        }
    )
    by_model = vectors_by_model(table)
    assert set(by_model["muq"]) == {"a" * 64, "c" * 64}
    assert set(by_model["clap"]) == {"d" * 64}
    # A model's neighbour lists only contain assets that model embedded.
    muq = neighbours(ASSETS, by_model["muq"])
    assert {n.sha256 for items in muq.values() for n in items} <= set(by_model["muq"])


def test_perfect_self_retrieval():
    r = self_retrieval(ASSETS, VECTORS)
    assert (r.seeds, r.recall_at_1, r.recall_at_10) == (1, 1.0, 1.0)


def test_failed_self_retrieval():
    vectors = dict(VECTORS)
    vectors["b" * 64] = _unit(0, 0.05, 1)  # the preview now sits next to C's full track
    r = self_retrieval(ASSETS, vectors)
    assert r.recall_at_1 == 0.0 and r.recall_at_10 == 1.0
