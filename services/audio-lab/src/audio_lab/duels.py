"""Blind A/B duels: two models' rank-matched picks for one seed, for the owner to choose."""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

from .neighbours import Neighbour


@dataclass(frozen=True)
class Duel:
    seed: str
    rank: int
    left_model: str
    left: Neighbour
    right_model: str
    right: Neighbour


def _first_difference(a: list[Neighbour], b: list[Neighbour]) -> int | None:
    for rank, (x, y) in enumerate(zip(a, b, strict=False)):
        if x.seed != y.seed:
            return rank
    return None


def build_duels(
    lists_by_model: dict[str, dict[str, list[Neighbour]]],
    run_id: str,
    models: list[str] | None = None,
) -> list[Duel]:
    """At most one duel per seed and model pair, ordered and sided by the run ID.

    Each pair's duels are shuffled, then taken round-robin across pairs, so any prefix the
    owner judges covers every pair about equally. The generator only orders the page.
    """

    rng = random.Random(run_id)
    per_pair: list[list[Duel]] = []
    for a, b in itertools.combinations(sorted(models or lists_by_model), 2):
        duels = []
        for seed in sorted(lists_by_model[a].keys() & lists_by_model[b].keys()):
            la, lb = lists_by_model[a][seed], lists_by_model[b][seed]
            rank = _first_difference(la, lb)
            if rank is None:
                continue
            sides = [(a, la[rank]), (b, lb[rank])]
            rng.shuffle(sides)
            duels.append(Duel(seed, rank, sides[0][0], sides[0][1], sides[1][0], sides[1][1]))
        rng.shuffle(duels)
        per_pair.append(duels)
    rng.shuffle(per_pair)
    ordered = []
    for round_ in itertools.zip_longest(*per_pair):
        ordered.extend(d for d in round_ if d is not None)
    return ordered
