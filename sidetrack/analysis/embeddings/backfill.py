"""Queue embedding for assets that need it. Only the operator starts it (`audio embed`)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from sidetrack.analysis.models import AudioAsset, AudioEmbedding
from sidetrack.queue_client import enqueue

from .jobs import BATCH_SIZE, QUEUE, TASK
from .registry import PIPELINE, enabled_model


@dataclass(frozen=True)
class Backfill:
    model: str
    assets: int
    job_ids: list[UUID]


def assets_needing_embedding(db: Session, model: str, audio_dir: Path) -> list[UUID]:
    """Assets with a file on disk and no embedding at the model's current revision and pipeline."""

    spec = enabled_model(model)
    current = and_(
        AudioEmbedding.asset_id == AudioAsset.id,
        AudioEmbedding.model == spec.name,
        AudioEmbedding.checkpoint_revision == spec.revision,
        AudioEmbedding.pipeline == PIPELINE,
    )
    rows = db.execute(
        select(AudioAsset.id, AudioAsset.path)
        .outerjoin(AudioEmbedding, current)
        .where(AudioAsset.file_deleted_at.is_(None), AudioEmbedding.id.is_(None))
        .order_by(AudioAsset.fetched_at, AudioAsset.id)
    ).all()
    return [asset_id for asset_id, path in rows if (audio_dir / path).is_file()]


def queue_backfill(
    db: Session,
    model: str,
    audio_dir: Path,
    *,
    limit: int | None = None,
    batch_size: int = BATCH_SIZE,
    requested_by: UUID | None = None,
) -> Backfill:
    """Queue `analysis.embed_audio` jobs on the gpu queue in batches. The caller commits."""

    spec = enabled_model(model)
    asset_ids = assets_needing_embedding(db, spec.name, audio_dir)[:limit]
    job_ids = []
    for start in range(0, len(asset_ids), batch_size):
        batch = [str(a) for a in asset_ids[start : start + batch_size]]
        job = enqueue(
            db,
            TASK,
            {"model": spec.name, "asset_ids": batch},
            queue=QUEUE,
            requested_by=requested_by,
        )
        job_ids.append(job.id)
    return Backfill(spec.name, len(asset_ids), job_ids)
