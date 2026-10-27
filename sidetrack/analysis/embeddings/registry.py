"""Audio embedding models Sidetrack may run (ADR 0004; openspec analysis/audio-embeddings).

Only enabled models are embedded. Vectors from different models, revisions or pipelines
are never compared. Pins match services/audio-lab, which benchmarked them.
"""

from __future__ import annotations

from dataclasses import dataclass

# Decoding, 10 s windows (3 s minimum tail), full tracks capped at 180 s, fp32, mean over
# windows, L2 normalised. Bump it whenever preprocessing changes: older vectors go stale.
PIPELINE = "w10-t3-cap180-fp32-mean-l2-v1"
WINDOW_S = 10.0
MIN_TAIL_S = 3.0
MAX_FULL_S = 180.0


@dataclass(frozen=True)
class EmbeddingModel:
    name: str
    checkpoint: str
    revision: str
    license: str
    sample_rate: int
    dim: int


MUQ_MULAN = EmbeddingModel(
    name="muq-mulan",
    checkpoint="OpenMuQ/MuQ-MuLan-large",
    revision="2e01c796b71dca71b45251384c04cd7b237c9020",
    license="CC-BY-NC-4.0",
    sample_rate=24000,
    dim=512,
)

ENABLED: dict[str, EmbeddingModel] = {MUQ_MULAN.name: MUQ_MULAN}


class ModelUnavailable(Exception):
    """Libraries, weights or the GPU are missing. The job fails as `unavailable`, no retry."""


class ModelNotEnabled(ValueError):
    """The requested model isn't on the enabled list."""


def enabled_model(name: str) -> EmbeddingModel:
    try:
        return ENABLED[name]
    except KeyError:
        enabled = ", ".join(ENABLED)
        raise ModelNotEnabled(f"model {name!r} is not enabled; enabled: {enabled}") from None
