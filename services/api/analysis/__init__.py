"""Analysis utilities for computing taste profiles and related summaries."""

from .compatibility import compute_compatibility_score, upsert_compatibility
from .constants import FEATURE_FIELDS
from .taste import (
    TasteFingerprint,
    compute_genre_histogram,
    compute_profile_summary,
    compute_user_taste_profile,
)

__all__ = [
    "FEATURE_FIELDS",
    "TasteFingerprint",
    "compute_genre_histogram",
    "compute_profile_summary",
    "compute_user_taste_profile",
    "compute_compatibility_score",
    "upsert_compatibility",
]
