"""Public analysis interface. Exported ORM models are for cross-domain reads."""

from .compatibility import compute_compatibility_score, upsert_compatibility
from .constants import FEATURE_FIELDS
from .embeddings import Neighbours, embed_assets, similar_assets
from .models import Compatibility, TasteProfile, TrackFeature, UserRecommendation
from .taste import (
    TasteFingerprint,
    compute_genre_histogram,
    compute_profile_summary,
    compute_user_taste_profile,
)

__all__ = [
    "TrackFeature",
    "TasteProfile",
    "Compatibility",
    "UserRecommendation",
    "Neighbours",
    "embed_assets",
    "similar_assets",
    "compute_user_taste_profile",
    "compute_compatibility_score",
    "upsert_compatibility",
    "FEATURE_FIELDS",
    "TasteFingerprint",
    "compute_genre_histogram",
    "compute_profile_summary",
]
