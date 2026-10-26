"""Compatibility score computation between two users."""

from __future__ import annotations

import math
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from sidetrack.analysis.models import Compatibility, TasteProfile


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float | None:
    """Cosine similarity between two feature-mean dicts. Returns None if vectors are empty."""
    keys = [k for k in a if k in b and a[k] is not None and b[k] is not None]
    if not keys:
        return None

    dot = sum(a[k] * b[k] for k in keys)
    mag_a = math.sqrt(sum(a[k] ** 2 for k in keys))
    mag_b = math.sqrt(sum(b[k] ** 2 for k in keys))

    if mag_a == 0 or mag_b == 0:
        return None

    return dot / (mag_a * mag_b)


def _genre_overlap(a: dict[str, float], b: dict[str, float]) -> float:
    """Compute genre overlap as sum of min weights for shared genres."""
    shared = set(a) & set(b)
    if not shared:
        return 0.0
    return sum(min(a[g], b[g]) for g in shared)


def compute_compatibility_score(
    db: Session, user_a_id: UUID, user_b_id: UUID
) -> tuple[float, dict]:
    """Compute a 0-100 compatibility score between two users.

    Uses feature-vector cosine similarity if taste profiles with feature_means are
    available; falls back to genre overlap otherwise.

    Returns (score, details).
    """
    profile_a = db.execute(
        select(TasteProfile).where(
            TasteProfile.user_id == user_a_id, TasteProfile.scope == "all_time"
        )
    ).scalar_one_or_none()

    profile_b = db.execute(
        select(TasteProfile).where(
            TasteProfile.user_id == user_b_id, TasteProfile.scope == "all_time"
        )
    ).scalar_one_or_none()

    details: dict = {}
    score: float

    if profile_a and profile_b and profile_a.feature_means and profile_b.feature_means:
        sim = _cosine_similarity(profile_a.feature_means, profile_b.feature_means)
        if sim is not None:
            score = round(sim * 100, 1)
            details["method"] = "cosine_similarity"
            details["feature_similarity"] = sim
        else:
            score = 0.0
            details["method"] = "no_features"
    elif profile_a and profile_b and profile_a.genre_histogram and profile_b.genre_histogram:
        overlap = _genre_overlap(profile_a.genre_histogram, profile_b.genre_histogram)
        score = round(min(overlap * 100, 100), 1)
        details["method"] = "genre_overlap"
        details["genre_overlap"] = overlap
    else:
        score = 0.0
        details["method"] = "no_data"

    return score, details


def upsert_compatibility(db: Session, user_a_id: UUID, user_b_id: UUID) -> Compatibility:
    """Compute and persist (or update) a compatibility record."""
    # Ensure consistent ordering so (A,B) and (B,A) map to the same row
    lo, hi = (user_a_id, user_b_id) if user_a_id < user_b_id else (user_b_id, user_a_id)

    score, details = compute_compatibility_score(db, user_a_id, user_b_id)

    existing = db.execute(
        select(Compatibility).where(Compatibility.user_a_id == lo, Compatibility.user_b_id == hi)
    ).scalar_one_or_none()

    if existing:
        existing.score = score
        existing.details = details
    else:
        existing = Compatibility(user_a_id=lo, user_b_id=hi, score=score, details=details)
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing
