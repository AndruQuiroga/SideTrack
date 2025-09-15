"""Compute interpretable track scores from features and embeddings."""

from __future__ import annotations

from collections.abc import Sequence

from .config import SCORING_CONFIG, Calibration, ScoringConfig


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


def _calibrate(raw: float, cal: Calibration) -> float:
    val = cal.scale * raw + cal.bias
    if val < 0.0:
        return 0.0
    if val > 1.0:
        return 1.0
    return float(val)


def compute_axes(
    features: dict[str, float],
    embeddings: dict[str, Sequence[float]],
    *,
    model: str,
    config: ScoringConfig | None = None,
) -> dict[str, float]:
    """Return interpretable axes from available data."""

    cfg = config or SCORING_CONFIG
    scores: dict[str, float] = {}

    # Feature-based metrics
    if "pumpiness" in features:
        scores["energy"] = _calibrate(
            float(features.get("pumpiness", 0.0)), cfg.calibration["energy"]
        )
    if "bpm" in features:
        scores["danceability"] = _calibrate(
            float(features.get("bpm", 0.0)), cfg.calibration["danceability"]
        )

    # Embedding-based metrics
    vec = embeddings.get(model)
    if vec is not None:
        axes = cfg.axes.get(model, {})
        if "valence" in axes:
            scores["valence"] = _calibrate(_dot(vec, axes["valence"]), cfg.calibration["valence"])
        if "acousticness" in axes:
            scores["acousticness"] = _calibrate(
                _dot(vec, axes["acousticness"]), cfg.calibration["acousticness"]
            )

    return scores
