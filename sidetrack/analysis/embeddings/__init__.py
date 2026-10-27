"""Audio embeddings (openspec analysis/audio-embeddings). Importing this needs no numpy or torch.

`embed_assets` decodes and runs the model only inside the gpu job; the GPU worker image
(services/gpu-worker) provides those libraries.
"""

from .backfill import Backfill, assets_needing_embedding, queue_backfill
from .jobs import BATCH_SIZE, QUEUE, TASK, TIME_LIMIT_S, embed_assets, is_current
from .neighbours import Neighbour, Neighbours, resolve_asset, similar_assets
from .registry import (
    ENABLED,
    PIPELINE,
    EmbeddingModel,
    ModelNotEnabled,
    ModelUnavailable,
    enabled_model,
)

__all__ = [
    "Backfill",
    "assets_needing_embedding",
    "queue_backfill",
    "resolve_asset",
    "BATCH_SIZE",
    "ENABLED",
    "PIPELINE",
    "QUEUE",
    "TASK",
    "TIME_LIMIT_S",
    "EmbeddingModel",
    "ModelNotEnabled",
    "ModelUnavailable",
    "Neighbour",
    "Neighbours",
    "embed_assets",
    "enabled_model",
    "is_current",
    "similar_assets",
]
