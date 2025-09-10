"""User profile utilities for re-ranking candidates."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from math import sqrt
from statistics import median


__all__ = [
    "compute_recent_profile",
    "compute_discovery",
    "rerank_vector",
]


def compute_recent_profile(tracks: Sequence[dict[str, float]]) -> dict[str, float]:
    """Return median tempo, valence, and energy for recent tracks."""

    tempos = [t["tempo"] for t in tracks if "tempo" in t]
    valences = [t["valence"] for t in tracks if "valence" in t]
    energies = [t["energy"] for t in tracks if "energy" in t]
    profile: dict[str, float] = {}
    if tempos:
        profile["tempo"] = float(median(tempos))
    if valences:
        profile["valence"] = float(median(valences))
    if energies:
        profile["energy"] = float(median(energies))
    return profile


def compute_discovery(
    history: Sequence[dict[str, object]], *, now: datetime | None = None
) -> dict[str, float]:
    """Return discovery percentages for the last four weeks.

    Each item in ``history`` must provide ``played_at`` (``datetime`` or ISO
    timestamp string), ``artist``, and ``label`` entries.
    """

    now = now or datetime.utcnow()
    cutoff = now - timedelta(weeks=4)

    old_artists: set[str] = set()
    old_labels: set[str] = set()
    recent: list[dict[str, object]] = []

    for item in history:
        played_at = item.get("played_at")
        if isinstance(played_at, str):
            played_at = datetime.fromisoformat(played_at)
        if not isinstance(played_at, datetime):
            continue
        if played_at < cutoff:
            if artist := item.get("artist"):
                old_artists.add(str(artist))
            if label := item.get("label"):
                old_labels.add(str(label))
        else:
            recent.append(item)

    recent_artists = {str(it.get("artist")) for it in recent if it.get("artist")}
    recent_labels = {str(it.get("label")) for it in recent if it.get("label")}

    new_artists = recent_artists - old_artists
    new_labels = recent_labels - old_labels

    new_artist_pct = (
        len(new_artists) / len(recent_artists) * 100.0 if recent_artists else 0.0
    )
    new_label_pct = (
        len(new_labels) / len(recent_labels) * 100.0 if recent_labels else 0.0
    )

    return {"new_artist_pct": new_artist_pct, "new_label_pct": new_label_pct}


def rerank_vector(
    candidate: dict[str, float | str],
    profile: dict[str, float],
    known_artists: set[str],
    known_labels: set[str],
) -> list[float]:
    """Return ``[cf_score, novelty, diversity, profile_match]`` for a candidate."""

    cf_score = float(candidate.get("cf_score", 0.0))
    novelty = 1.0 if str(candidate.get("artist")) not in known_artists else 0.0
    diversity = 1.0 if str(candidate.get("label")) not in known_labels else 0.0

    dist = sqrt(
        sum(
            (
                float(candidate.get(key, 0.0)) - float(profile.get(key, 0.0))
            )
            ** 2
            for key in ("tempo", "valence", "energy")
        )
    )
    profile_match = 1.0 / (1.0 + dist)

    return [cf_score, novelty, diversity, profile_match]
