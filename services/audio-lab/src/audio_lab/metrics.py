"""Metrics that describe each model's neighbour lists without the owner's judgement."""

from __future__ import annotations

import itertools
import re

import numpy as np

from .manifest import Asset, _norm
from .neighbours import Neighbour

# Same split as sidetrack.analysis.audio.verify; the lab never imports sidetrack.
_CREDIT_SPLIT = re.compile(
    r"\s*(?:,|&|\+|/|\bx\b|\bfeat\.?|\bft\.?|\bfeaturing\b|\bwith\b)\s*", re.I
)


def credited_artists(text: str) -> set[str]:
    return {n for part in _CREDIT_SPLIT.split(text) if (n := _norm(part))}


def same_artist_rate(
    assets: list[Asset], lists: dict[str, list[Neighbour]]
) -> tuple[float | None, int]:
    """Mean share of a seed's same-artist seeds found in its list, over seeds that have any."""

    credits = {a.seed: credited_artists(a.artist) for a in assets}
    shares = []
    for seed, items in lists.items():
        peers = {s for s, c in credits.items() if s != seed and c & credits[seed]}
        if peers:
            shares.append(len(peers & {n.seed for n in items}) / len(peers))
    return (float(np.mean(shares)) if shares else None), len(shares)


def separation(scores_by_seed: dict[str, np.ndarray]) -> float | None:
    """Mean gap between each seed's best and median similarity to the other tracks."""

    gaps = [float(s.max() - np.median(s)) for s in scores_by_seed.values() if s.size]
    return float(np.mean(gaps)) if gaps else None


def overlap(lists_by_model: dict[str, dict[str, list[Neighbour]]]) -> dict[str, float]:
    """Pair key "a|b" → mean share of neighbours two models have in common."""

    out = {}
    for a, b in itertools.combinations(sorted(lists_by_model), 2):
        la, lb = lists_by_model[a], lists_by_model[b]
        shared = [
            len({n.seed for n in la[s]} & {n.seed for n in lb[s]}) / max(len(la[s]), 1)
            for s in la.keys() & lb.keys()
        ]
        if shared:
            out[f"{a}|{b}"] = round(float(np.mean(shared)), 4)
    return out
