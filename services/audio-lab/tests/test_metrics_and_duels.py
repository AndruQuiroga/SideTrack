"""Spec: automatic metrics describe neighbour lists; duels compare rank-matched picks."""

from __future__ import annotations

import numpy as np
import pytest

from audio_lab.duels import build_duels
from audio_lab.manifest import Asset
from audio_lab.metrics import (
    colisten_hit_rate,
    credited_artists,
    genre_precision,
    overlap,
    same_artist_rate,
    separation,
    sleep_purity,
)
from audio_lab.neighbours import Neighbour


def _asset(artist: str, title: str) -> Asset:
    return Asset(
        f"{title}.wav", title, "full", "test", title, 200.0, "confirmed", None, artist, title
    )


def _list(*seeds: str) -> list[Neighbour]:
    return [Neighbour(s, s, 1.0 - i / 10) for i, s in enumerate(seeds)]


def test_same_artist_found():
    assets = [_asset("Dabin", "Alive"), _asset("Dabin & Dia Frampton", "Hold"), _asset("X", "Y")]
    alive, hold, other = (a.seed for a in assets)
    lists = {alive: _list(hold, other), hold: _list(alive, other), other: _list(alive, hold)}

    rate, rated = same_artist_rate(assets, lists)

    assert (rate, rated) == (1.0, 2)  # X has no same-artist seed, so it isn't counted
    assert credited_artists("Trivecta x MitiS feat. Someone") == {"trivecta", "mitis", "someone"}


def test_same_artist_missed():
    assets = [_asset("Dabin", "Alive"), _asset("Dabin", "Hold"), _asset("X", "Y")]
    alive, hold, other = (a.seed for a in assets)
    lists = {alive: _list(other), hold: _list(other), other: _list(alive)}
    assert same_artist_rate(assets, lists) == (0.0, 2)


def test_identical_lists_overlap_fully():
    lists = {"s1": _list("a", "b"), "s2": _list("b", "c")}
    assert overlap({"muq": lists, "mert": dict(lists)}) == {"mert|muq": 1.0}
    assert overlap({"muq": lists, "mert": {"s1": _list("x", "y"), "s2": _list("c", "z")}}) == {
        "mert|muq": 0.25
    }


def test_separation_is_best_minus_median():
    assert separation({"s": np.array([0.9, 0.5, 0.4], dtype=np.float32)}) == pytest.approx(0.4)


def test_duel_uses_first_rank_where_models_differ():
    lists = {
        "muq": {"seed": _list("x", "y", "w")},
        "mert": {"seed": _list("x", "z", "w")},
    }
    (duel,) = build_duels(lists, "run-1")

    assert duel.rank == 1
    picks = {duel.left_model: duel.left.seed, duel.right_model: duel.right.seed}
    assert picks == {"muq": "y", "mert": "z"}


def test_agreeing_lists_have_no_duel():
    same = {"seed": _list("x", "y")}
    assert build_duels({"muq": same, "mert": dict(same)}, "run-1") == []


def test_order_and_sides_fixed_by_run_and_spread_across_pairs():
    models = ["a", "b", "c"]
    lists = {m: {f"s{i}": _list(f"{m}{i}", "shared") for i in range(5)} for m in models}
    first = build_duels(lists, "run-1")

    assert first == build_duels(lists, "run-1")
    assert first != build_duels(lists, "run-2")
    assert len(first) == 15  # 5 seeds × 3 pairs
    opening = {frozenset((d.left_model, d.right_model)) for d in first[:3]}
    assert len(opening) == 3  # the first round covers every pair
    assert {d.left_model for d in first} == set(models)  # sides vary


def test_perfect_genre_separation():
    rock = [_asset(f"R{i}", f"rock {i}") for i in range(3)]
    jazz = [_asset(f"J{i}", f"jazz {i}") for i in range(3)]
    personal = _asset("Me", "mine")
    vectors = {a.sha256: np.array([1.0, 0.1 * i], dtype=np.float32) for i, a in enumerate(rock)}
    vectors |= {a.sha256: np.array([0.1 * i, 1.0], dtype=np.float32) for i, a in enumerate(jazz)}
    vectors[personal.sha256] = np.array([0.0, 1.0], dtype=np.float32)
    labels = {a.seed: {"genre:Rock"} for a in rock} | {a.seed: {"genre:Jazz"} for a in jazz}

    # k=2: each control seed's two nearest *control* tracks; the personal track never counts.
    assert genre_precision([*rock, *jazz, personal], vectors, labels, k=2) == (1.0, 6)


def test_colisten_one_direction_found():
    lists = {"a": _list("b", "x"), "b": _list("x", "y")}
    assert colisten_hit_rate(lists, [("a", "b")]) == (0.5, 1)


def test_sleep_purity_against_base_rate():
    seeds = [f"s{i}" for i in range(20)]
    sleepy = {"s0", "s1"}  # 10% of the pool
    others = [s for s in seeds if s not in sleepy]
    lists = {s: _list(*others[:10]) for s in seeds}
    lists["s0"] = _list(*[f"t{i}" for i in range(6)], *others[:4])
    lists["s1"] = _list(*[f"t{i}" for i in range(6)], *others[:4])
    labels = {s: {"sleep"} for s in sleepy} | {f"t{i}": {"sleep"} for i in range(6)}

    purity, base, count = sleep_purity(lists, labels)
    assert (purity, base, count) == (pytest.approx(0.6), pytest.approx(0.1), 2)


def test_duels_only_between_chosen_models():
    lists = {m: {f"s{i}": _list(f"{m}{i}", "shared") for i in range(4)} for m in "abc"}
    duels = build_duels(lists, "run-1", ["a", "c"])
    assert len(duels) == 4
    assert all({d.left_model, d.right_model} == {"a", "c"} for d in duels)
