from __future__ import annotations

"""Compute basic scores from features/embeddings."""

from typing import Dict


def compute_scores(features: dict, embeddings: dict) -> Dict[str, float]:
    """Dummy scoring function used for tests."""
    scores: Dict[str, float] = {}
    if "pumpiness" in features:
        scores["energy"] = float(features["pumpiness"])
    if embeddings:
        first_key = next(iter(embeddings))
        scores["embedding_norm"] = float(sum(x * x for x in embeddings[first_key]))
    return scores
