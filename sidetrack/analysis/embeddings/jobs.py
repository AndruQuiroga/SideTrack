"""Embed a batch of audio assets with one model (the `analysis.embed_audio` gpu job)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from sidetrack.analysis.models import AudioAsset, AudioEmbedding
from sidetrack.config import get_settings
from sidetrack.db import database_now
from sidetrack.types import AudioKind

from .registry import MAX_FULL_S, PIPELINE, EmbeddingModel, enabled_model

TASK = "analysis.embed_audio"
QUEUE = "gpu"
BATCH_SIZE = 128  # run 20261027-172855-0c32766-dirty: at most ~313 s per batch on the GTX 1070
TIME_LIMIT_S = 1800


class Adapter(Protocol):
    spec: EmbeddingModel

    def load(self, device: str) -> None: ...

    def embed_windows(self, batch: list[Any]) -> Any: ...


def is_current(row: AudioEmbedding | None, spec: EmbeddingModel) -> bool:
    return row is not None and row.checkpoint_revision == spec.revision and row.pipeline == PIPELINE


def default_adapter(model: str) -> Adapter:
    from .muq_mulan import MuQMuLan

    if model != MuQMuLan.spec.name:
        raise NotImplementedError(model)
    return MuQMuLan()


def embed_assets(
    db: Session,
    model: str,
    asset_ids: Sequence[UUID],
    *,
    adapter: Adapter | None = None,
    audio_dir: Path | None = None,
    device: str | None = None,
    job_id: UUID | None = None,
) -> dict[str, Any]:
    """Embed the assets that need it; skip the rest with a reason. Never commits.

    The model loads only if some asset needs embedding. If it can't load, ModelUnavailable
    propagates before any row is written.
    """

    spec = enabled_model(model)
    settings = get_settings()
    audio_dir = audio_dir or settings.sidetrack_audio_dir
    assets = {a.id: a for a in db.scalars(select(AudioAsset).where(AudioAsset.id.in_(asset_ids)))}
    existing = {
        e.asset_id: e
        for e in db.scalars(
            select(AudioEmbedding).where(
                AudioEmbedding.asset_id.in_(asset_ids), AudioEmbedding.model == spec.name
            )
        )
    }
    current: list[str] = []
    skipped: list[dict[str, str]] = []
    todo: list[tuple[AudioAsset, Path]] = []
    for asset_id in asset_ids:
        asset = assets.get(asset_id)
        if asset is None:
            skipped.append({"asset_id": str(asset_id), "reason": "asset_not_found"})
        elif is_current(existing.get(asset_id), spec):
            current.append(str(asset_id))
        elif asset.file_deleted_at is not None:
            skipped.append({"asset_id": str(asset_id), "reason": "file_deleted"})
        elif audio_dir is None or not (Path(audio_dir) / asset.path).is_file():
            skipped.append({"asset_id": str(asset_id), "reason": "missing_file"})
        else:
            todo.append((asset, Path(audio_dir) / asset.path))

    embedded: list[str] = []
    if todo:
        from . import audio  # numpy, soundfile and soxr: only where embedding actually runs

        adapter = adapter or default_adapter(spec.name)
        adapter.load(device or settings.sidetrack_gpu_device)
        for asset, path in todo:
            try:
                wave = audio.decode(path, spec.sample_rate)
            except audio.DecodeError:
                skipped.append({"asset_id": str(asset.id), "reason": "decode_failed"})
                continue
            max_s = MAX_FULL_S if asset.kind == AudioKind.FULL else None
            vector = audio.pool(
                adapter.embed_windows(audio.windows(wave, spec.sample_rate, max_s=max_s))
            )
            row = existing.get(asset.id) or AudioEmbedding(asset_id=asset.id, model=spec.name)
            row.checkpoint_revision = spec.revision
            row.pipeline = PIPELINE
            row.dim = int(vector.shape[0])
            row.embedding = [float(x) for x in vector]
            row.job_id = job_id
            row.embedded_at = database_now(db)
            db.add(row)
            embedded.append(str(asset.id))
        db.flush()

    return {
        "model": spec.name,
        "revision": spec.revision,
        "pipeline": PIPELINE,
        "embedded": embedded,
        "already_current": current,
        "skipped": skipped,
    }
