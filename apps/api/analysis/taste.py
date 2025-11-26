"""Taste profile aggregation helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.models import ListenEvent, TasteProfile, TrackFeature

FEATURE_FIELDS = [
    "energy",
    "valence",
    "danceability",
    "tempo",
    "acousticness",
    "instrumentalness",
]


@dataclass
class TasteFingerprint:
    """Simple serializable fingerprint for visualizations."""

    labels: list[str]
    values: list[float]


def _collect_feature_summaries(
    listen_events: Iterable[ListenEvent],
    track_features: Mapping[UUID, TrackFeature],
) -> tuple[dict[str, float], dict[str, int], int, set[UUID]]:
    """Aggregate raw sums/counts for feature means.

    Returns (sums, counts, missing_feature_listens, tracks_with_features).
    """

    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    missing_feature_listens = 0
    tracks_with_features: set[UUID] = set()

    for listen in listen_events:
        features = track_features.get(listen.track_id)
        if features is None:
            missing_feature_listens += 1
            continue

        tracks_with_features.add(listen.track_id)
        for field in FEATURE_FIELDS:
            value = getattr(features, field)
            if value is None:
                continue
            sums[field] += float(value)
            counts[field] += 1

    return sums, counts, missing_feature_listens, tracks_with_features


def compute_genre_histogram(
    listen_events: Iterable[ListenEvent],
    track_features: Mapping[UUID, TrackFeature],
) -> dict[str, float]:
    """Compute a normalized histogram of genres across listens."""

    genre_counts: Counter[str] = Counter()
    for listen in listen_events:
        features = track_features.get(listen.track_id)
        if not features or not features.genres:
            continue
        genre_counts.update(features.genres)

    total = sum(genre_counts.values())
    if total == 0:
        return {}

    return {genre: count / total for genre, count in genre_counts.items()}


def _build_fingerprint(feature_means: dict[str, float | None]) -> TasteFingerprint | None:
    labels: list[str] = []
    values: list[float] = []
    for field in FEATURE_FIELDS:
        value = feature_means.get(field)
        if value is None:
            continue
        labels.append(field)
        values.append(float(value))

    if not labels:
        return None

    return TasteFingerprint(labels=labels, values=values)


def compute_profile_summary(
    listen_events: Iterable[ListenEvent],
    track_features: Mapping[UUID, TrackFeature],
) -> dict:
    """Compute a serializable summary for a user's taste profile."""

    listens = list(listen_events)
    sums, counts, missing_feature_listens, tracks_with_features = _collect_feature_summaries(
        listens, track_features
    )
    feature_means: dict[str, float | None] = {}
    for field in FEATURE_FIELDS:
        if counts.get(field):
            feature_means[field] = sums[field] / counts[field]
        else:
            feature_means[field] = None

    genre_histogram = compute_genre_histogram(listen_events, track_features)
    fingerprint = _build_fingerprint(feature_means)

    return {
        "listen_count": len(listens),
        "tracks_with_features": len(tracks_with_features),
        "missing_feature_listens": missing_feature_listens,
        "feature_means": feature_means,
        "genre_histogram": genre_histogram,
        "fingerprint": fingerprint.__dict__ if fingerprint else None,
    }


def compute_user_taste_profile(
    db: Session, user_id: UUID, scope: str = "all_time"
) -> TasteProfile:
    """Compute and upsert a taste profile for the given user."""

    listens = db.scalars(select(ListenEvent).where(ListenEvent.user_id == user_id)).all()
    track_ids = {listen.track_id for listen in listens}
    features: list[TrackFeature] = []
    if track_ids:
        features = db.scalars(
            select(TrackFeature).where(TrackFeature.track_id.in_(track_ids))
        ).all()

    feature_map = {feat.track_id: feat for feat in features}
    summary = compute_profile_summary(listens, feature_map)

    existing = db.scalars(
        select(TasteProfile).where(
            TasteProfile.user_id == user_id,
            TasteProfile.scope == scope,
        )
    ).first()

    if existing:
        existing.summary = summary
        existing.updated_at = datetime.now(timezone.utc)
        profile = existing
    else:
        profile = TasteProfile(user_id=user_id, scope=scope, summary=summary)
        db.add(profile)

    db.commit()
    db.refresh(profile)
    return profile
