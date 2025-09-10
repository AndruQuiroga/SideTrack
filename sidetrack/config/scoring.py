"""Calibration constants for track scoring."""

from dataclasses import dataclass, field


@dataclass
class Calibration:
    """Linear calibration parameters for a score."""

    scale: float = 1.0
    bias: float = 0.0


@dataclass
class ScoringConfig:
    """Configuration holding scoring axes and calibration."""

    # Embedding axis vectors per model and metric
    axes: dict[str, dict[str, list[float]]] = field(
        default_factory=lambda: {
            "test": {
                "valence": [1.0, 0.0, 0.0],
                "acousticness": [0.0, 1.0, 0.0],
            }
        }
    )
    # Calibration constants per metric
    calibration: dict[str, Calibration] = field(
        default_factory=lambda: {
            "energy": Calibration(),
            "danceability": Calibration(scale=1 / 200.0),
            "valence": Calibration(),
            "acousticness": Calibration(),
        }
    )


# default instance used throughout the application
SCORING_CONFIG = ScoringConfig()
