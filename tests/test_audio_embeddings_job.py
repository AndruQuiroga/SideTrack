"""Spec: analysis/audio-embeddings: the embedding job, the gpu lane and unavailable models."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
import pytest
import soundfile
from embedding_doubles import HashEmbedder, UnloadableEmbedder
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session
from test_audio_embeddings_store import make_asset
from test_worker_recovery import await_status

from sidetrack.analysis import embed_assets
from sidetrack.analysis.embeddings import PIPELINE, TASK, ModelUnavailable
from sidetrack.analysis.embeddings.registry import MUQ_MULAN
from sidetrack.analysis.models import AudioAsset, AudioEmbedding
from sidetrack.queue_client import enqueue
from sidetrack.queue_models import BackgroundJob, JobSchedule
from sidetrack.types import AudioKind

pytestmark = pytest.mark.unit


def tone(seconds: float, freq: float, rate: int = 24000) -> np.ndarray:
    t = np.arange(int(seconds * rate)) / rate
    return (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def asset_with_file(db, audio_dir, freq, **overrides):
    name = f"{uuid4().hex}.wav"
    soundfile.write(str(audio_dir / name), tone(12.0, freq), 24000)
    return make_asset(db, path=name, **overrides)


def rows(db, asset_ids):
    return {
        e.asset_id: e
        for e in db.scalars(select(AudioEmbedding).where(AudioEmbedding.asset_id.in_(asset_ids)))
    }


def test_embedding_an_asset_records_provenance(db, tmp_path):
    asset = asset_with_file(db, tmp_path, 220)
    job_id = uuid4()

    result = embed_assets(
        db, "muq-mulan", [asset.id], adapter=HashEmbedder(), audio_dir=tmp_path, job_id=job_id
    )

    row = rows(db, [asset.id])[asset.id]
    assert result["embedded"] == [str(asset.id)]
    assert (row.model, row.checkpoint_revision, row.pipeline, row.dim) == (
        "muq-mulan",
        MUQ_MULAN.revision,
        PIPELINE,
        512,
    )
    assert float(np.linalg.norm(np.asarray(row.embedding))) == pytest.approx(1.0, abs=1e-5)
    assert row.job_id == job_id and row.embedded_at is not None


def test_batch_with_a_pruned_file(db, tmp_path):
    kept = [asset_with_file(db, tmp_path, f) for f in (220, 330)]
    pruned = asset_with_file(db, tmp_path, 440, file_deleted_at=datetime.now(UTC))
    ids = [a.id for a in [*kept, pruned]]

    result = embed_assets(db, "muq-mulan", ids, adapter=HashEmbedder(), audio_dir=tmp_path)

    assert set(rows(db, ids)) == {a.id for a in kept}
    assert result["skipped"] == [{"asset_id": str(pruned.id), "reason": "file_deleted"}]


def test_missing_and_undecodable_files_are_skipped(db, tmp_path):
    good = asset_with_file(db, tmp_path, 220)
    missing = make_asset(db, path="gone.webm")
    (tmp_path / "noise.wav").write_bytes(b"not audio at all")
    broken = make_asset(db, path="noise.wav")
    unknown = uuid4()
    ids = [good.id, missing.id, broken.id, unknown]

    result = embed_assets(db, "muq-mulan", ids, adapter=HashEmbedder(), audio_dir=tmp_path)

    assert result["embedded"] == [str(good.id)]
    assert {s["asset_id"]: s["reason"] for s in result["skipped"]} == {
        str(missing.id): "missing_file",
        str(broken.id): "decode_failed",
        str(unknown): "asset_not_found",
    }


def test_job_runs_twice(db, tmp_path):
    assets = [asset_with_file(db, tmp_path, f) for f in (220, 330)]
    ids = [a.id for a in assets]
    embed_assets(db, "muq-mulan", ids, adapter=HashEmbedder(), audio_dir=tmp_path)
    before = {k: (v.id, v.embedded_at, list(v.embedding)) for k, v in rows(db, ids).items()}

    again = HashEmbedder()
    result = embed_assets(db, "muq-mulan", ids, adapter=again, audio_dir=tmp_path)

    after = {k: (v.id, v.embedded_at, list(v.embedding)) for k, v in rows(db, ids).items()}
    assert after == before
    assert result["already_current"] == [str(i) for i in ids] and result["embedded"] == []
    assert again.loads == []  # nothing to do, so the model never loads


def test_revision_changed(db, tmp_path):
    asset = asset_with_file(db, tmp_path, 220)
    stale = AudioEmbedding(
        asset_id=asset.id,
        model="muq-mulan",
        checkpoint_revision="0000000",
        pipeline=PIPELINE,
        dim=2,
        embedding=[1.0, 0.0],
    )
    db.add(stale)
    db.flush()

    result = embed_assets(db, "muq-mulan", [asset.id], adapter=HashEmbedder(), audio_dir=tmp_path)

    row = rows(db, [asset.id])[asset.id]
    assert result["embedded"] == [str(asset.id)]
    assert row.id == stale.id and row.checkpoint_revision == MUQ_MULAN.revision and row.dim == 512


def test_previews_are_not_capped_but_full_tracks_are(db, tmp_path):
    name = f"{uuid4().hex}.wav"
    soundfile.write(str(tmp_path / name), tone(200.0, 220), 24000)
    full = make_asset(db, path=name, kind=AudioKind.FULL)
    preview = make_asset(db, path=name, kind=AudioKind.PREVIEW)

    full_embedder, preview_embedder = HashEmbedder(), HashEmbedder()
    embed_assets(db, "muq-mulan", [full.id], adapter=full_embedder, audio_dir=tmp_path)
    embed_assets(db, "muq-mulan", [preview.id], adapter=preview_embedder, audio_dir=tmp_path)

    assert full_embedder.windows_seen == 18 and preview_embedder.windows_seen == 20


def test_unloadable_model_writes_nothing(db, tmp_path):
    asset = asset_with_file(db, tmp_path, 220)
    with pytest.raises(ModelUnavailable):
        embed_assets(db, "muq-mulan", [asset.id], adapter=UnloadableEmbedder(), audio_dir=tmp_path)
    assert rows(db, [asset.id]) == {}


# The gpu lane end to end, with the real adapter: this environment has no torch.


@pytest.fixture()
def queued_embedding(engine, tmp_path):
    with Session(engine) as db:
        asset = asset_with_file(db, tmp_path, 220)
        job = enqueue(db, TASK, {"model": "muq-mulan", "asset_ids": [str(asset.id)]}, queue="gpu")
        db.commit()
        ids = asset.id, job.id, job.queue_job_id
        # The worker's maintenance seeds schedules; later tests expect only their own.
        schedules = set(db.scalars(select(JobSchedule.id)))
    try:
        yield ids
    finally:
        asset_id, job_id, queue_id = ids
        with engine.begin() as conn:
            conn.execute(delete(JobSchedule).where(JobSchedule.id.not_in(schedules)))
            conn.execute(delete(AudioAsset).where(AudioAsset.id == asset_id))
            conn.execute(text("SET LOCAL search_path TO job_queue,public"))
            conn.execute(text("DELETE FROM procrastinate_jobs WHERE id=:id"), {"id": queue_id})
            conn.execute(text("DELETE FROM background_jobs WHERE id=:id"), {"id": job_id})


def run_worker(database_url, audio_dir, queues):
    """A real `python -m sidetrack.worker --once`, as tests/test_worker_recovery.py starts it."""

    command = [sys.executable, "-m", "sidetrack.worker", "--once"]
    if queues:
        command += ["--queues", queues]
    return subprocess.Popen(
        command,
        env={**os.environ, "DATABASE_URL": database_url, "SIDETRACK_AUDIO_DIR": str(audio_dir)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def test_cpu_worker_leaves_embedding_queued(engine, database_url, tmp_path, queued_embedding):
    asset_id, job_id, _ = queued_embedding
    process = run_worker(database_url, tmp_path, None)  # default,musicbrainz
    assert process.wait(timeout=60) == 0
    with Session(engine) as db:
        assert db.get(BackgroundJob, job_id).status == "queued"
        assert rows(db, [asset_id]) == {}


def test_gpu_worker_without_cuda_reports_unavailable(
    engine, database_url, tmp_path, queued_embedding
):
    asset_id, job_id, _ = queued_embedding
    process = run_worker(database_url, tmp_path, "gpu")
    try:
        await_status(engine, job_id, "failed", timeout=60)
    finally:
        process.wait(timeout=60)
    with Session(engine) as db:
        job = db.get(BackgroundJob, job_id)
        assert (job.error, job.attempts, job.result) == ("unavailable", 1, None)
        assert rows(db, [asset_id]) == {}
