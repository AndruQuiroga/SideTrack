"""Metrics that describe each model's neighbour lists without the owner's judgement."""

from __future__ import annotations

import itertools
import re

import numpy as np

from .manifest import Asset, _norm
from .neighbours import Neighbour, similarities

# Same split as sidetrack.analysis.audio.verify; the lab never imports sidetrack.
CREDIT_SPLIT = re.compile(
    r"\s*(?:,|&|\+|/|\bx\b|\bfeat\.?|\bft\.?|\bfeaturing\b|\bwith\b)\s*", re.I
)


def credited_artists(text: str) -> set[str]:
    return {n for part in CREDIT_SPLIT.split(text) if (n := _norm(part))}


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


def genre_precision(
    assets: list[Asset], vectors: dict[str, np.ndarray], labels: dict[str, set[str]], k: int = 10
) -> tuple[float | None, int]:
    """Mean share of a control seed's k nearest *control* tracks that share its genre."""

    genre = {
        seed: next(iter(sorted(g for g in labs if g.startswith("genre:"))))
        for seed, labs in labels.items()
        if any(g.startswith("genre:") for g in labs)
    }
    control = [a for a in assets if a.seed in genre]
    shares = []
    for seed, (pool, scores) in similarities(control, vectors).items():
        order = np.argsort(-scores, kind="stable")[:k]
        if len(order):
            shares.append(float(np.mean([genre[pool[i].seed] == genre[seed] for i in order])))
    return (float(np.mean(shares)) if shares else None), len(shares)


def colisten_hit_rate(
    lists: dict[str, list[Neighbour]], pairs: list[tuple[str, str]]
) -> tuple[float | None, int]:
    """Share of pair directions (A→B, B→A) where the partner is in the track's list."""

    hits = []
    for a, b in pairs:
        for x, y in ((a, b), (b, a)):
            if x in lists:
                hits.append(y in {n.seed for n in lists[x]})
    return (float(np.mean(hits)) if hits else None), len(pairs)


def sleep_purity(
    lists: dict[str, list[Neighbour]], labels: dict[str, set[str]]
) -> tuple[float | None, float | None, int]:
    """(purity, base rate, sleep seeds): share of a sleep seed's neighbours labelled sleep."""

    sleepy = {s for s, labs in labels.items() if "sleep" in labs}
    pool = {s for s in lists}
    shares = [
        float(np.mean([n.seed in sleepy for n in lists[s]]))
        for s in sorted(sleepy & pool)
        if lists[s]
    ]
    if not shares:
        return None, None, 0
    base = len(sleepy & pool) / len(pool)
    return float(np.mean(shares)), base, len(shares)
