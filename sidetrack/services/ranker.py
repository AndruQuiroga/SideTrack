"""Ranking helpers for recommendation candidates."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .spotify import SpotifyUserClient


def artist_or_label(item: dict[str, Any]) -> str | None:
    """Return a key for diversity: artist or label.

    ``recording_by_isrc`` may attach either MusicBrainz identifiers or a label
    string to a candidate.  We favour MBIDs where available to keep the key
    stable.
    """

    return (
        item.get("artist_mbid")
        or item.get("artist")
        or item.get("label")
    )


async def profile_from_spotify(sp: SpotifyUserClient) -> dict[str, float]:
    """Return a simple audio feature profile for a Spotify user.

    The profile contains the mean tempo, valence and energy of the user's
    recently played tracks.  Missing values are ignored.
    """

    recent = await sp.get_recently_played()
    ids = [
        (item.get("track") or {}).get("id")
        for item in recent
        if (item.get("track") or {}).get("id")
    ]
    features = await sp.get_audio_features(ids) if ids else []

    tempos = [f.get("tempo") for f in features if isinstance(f.get("tempo"), int | float)]
    valences = [
        f.get("valence") for f in features if isinstance(f.get("valence"), int | float)
    ]
    energies = [
        f.get("energy") for f in features if isinstance(f.get("energy"), int | float)
    ]

    def _mean(vals: list[float]) -> float:
        return float(sum(vals) / len(vals)) if vals else 0.0

    return {
        "tempo": _mean(tempos),
        "valence": _mean(valences),
        "energy": _mean(energies),
    }


def mmr_diversity(
    items: list[dict[str, Any]],
    *,
    key: Callable[[dict[str, Any]], str | None] = artist_or_label,
    penalty: float = 0.3,
) -> list[dict[str, Any]]:
    """Penalise consecutive results sharing the same ``key``.

    The implementation is intentionally lightweight: items are processed in
    descending ``final_score`` order and a fixed penalty is subtracted when a
    key has been seen before.  The adjusted list is returned in the new order.
    """

    seen: dict[str | None, int] = {}
    ordered = sorted(
        items, key=lambda x: x.get("final_score", x.get("score_cf", 0.0)), reverse=True
    )
    out: list[dict[str, Any]] = []
    for item in ordered:
        k = key(item)
        dup_count = seen.get(k, 0)
        if dup_count:
            item["final_score"] = float(
                item.get("final_score", item.get("score_cf", 0.0)) - penalty * dup_count
            )
        else:
            item["final_score"] = float(item.get("final_score", item.get("score_cf", 0.0)))
        seen[k] = dup_count + 1
        out.append(item)
    return out


def rank(candidates: list[dict[str, Any]], user_profile: dict[str, float]) -> list[dict[str, Any]]:
    """Score and rerank ``candidates`` using ``user_profile``.

    Each candidate is given a ``final_score`` starting from its collaborative
    filtering score (``score_cf``).  When audio features for the candidate are
    available, they are compared against the user's profile and can slightly
    boost the score.  A list of ``reasons`` describing strong matches is also
    attached to each candidate.  Finally, :func:`mmr_diversity` is applied to
    reduce repetition by artist or label.
    """

    def _clamp(x: float) -> float:
        return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

    for cand in candidates:
        score = float(cand.get("score_cf") or 0.0)
        reasons: list[str] = []
        feats = cand.get("audio_features") or {}
        if feats and user_profile:
            tempo = feats.get("tempo")
            if tempo is not None and user_profile.get("tempo") is not None:
                diff = abs(float(tempo) - float(user_profile["tempo"]))
                score += 0.1 * _clamp(1 - diff / 200.0)
                if diff < 10:
                    reasons.append("tempo")
            for name in ("energy", "valence"):
                val = feats.get(name)
                prof_val = user_profile.get(name)
                if val is not None and prof_val is not None:
                    diff = abs(float(val) - float(prof_val))
                    score += 0.1 * _clamp(1 - diff)
                    if diff < 0.1:
                        reasons.append(name)
        cand["final_score"] = _clamp(score)
        cand["reasons"] = reasons

    ranked = mmr_diversity(candidates)
    ranked.sort(key=lambda x: x["final_score"], reverse=True)
    return ranked

