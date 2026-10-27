"""Spec: automatic metrics describe neighbour lists; duels compare rank-matched picks."""

from __future__ import annotations

import numpy as np
import pytest

from audio_lab.duels import build_duels
from audio_lab.manifest import Asset
from audio_lab.metrics import credited_artists, overlap, same_artist_rate, separation
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
