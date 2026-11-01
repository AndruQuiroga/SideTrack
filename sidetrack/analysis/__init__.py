"""Public analysis interface. Exported ORM models are for cross-domain reads."""

from .compatibility import compute_compatibility_score, upsert_compatibility
from .constants import FEATURE_FIELDS
from .embeddings import Neighbours, embed_assets, similar_assets
from .links import METHODS as LINK_METHODS
from .links import TASK as LINK_AUDIO_TASK
from .links import LinkReport, correct_link, link_audio, link_manually, report_json
from .models import Compatibility, TasteProfile, TrackFeature, UserRecommendation
from .resolution import REASONS as NO_AUDIO_REASONS
from .resolution import Coverage, TrackAudio, audio_coverage, audio_for_track
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
    "LinkReport",
    "Coverage",
    "TrackAudio",
    "audio_coverage",
    "audio_for_track",
    "correct_link",
    "link_audio",
    "link_manually",
    "LINK_AUDIO_TASK",
    "LINK_METHODS",
    "NO_AUDIO_REASONS",
    "report_json",
    "compute_user_taste_profile",
    "compute_compatibility_score",
    "upsert_compatibility",
    "FEATURE_FIELDS",
    "TasteFingerprint",
    "compute_genre_histogram",
    "compute_profile_summary",
]
