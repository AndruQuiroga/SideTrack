"""Spec: analysis/audio-embeddings: neighbours, backfill and the operator commands."""

from __future__ import annotations

import ast
import io
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select, text
from test_audio_embeddings_store import make_asset

from sidetrack.analysis import similar_assets
from sidetrack.analysis.embeddings import PIPELINE, TASK
from sidetrack.analysis.embeddings.registry import MUQ_MULAN
from sidetrack.analysis.models import AudioEmbedding
from sidetrack.audio import main
from sidetrack.config import Settings
from sidetrack.queue_maintenance import seed_cleanup
from sidetrack.queue_models import BackgroundJob, JobSchedule
from sidetrack.types import AudioKind

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]


def embed(db, asset, vector, *, model="muq-mulan", revision=MUQ_MULAN.revision):
    db.add(
        AudioEmbedding(
            asset_id=asset.id,
            model=model,
            checkpoint_revision=revision,
            pipeline=PIPELINE,
            dim=len(vector),
            embedding=vector,
        )
    )
    db.flush()


def names(result):
    return [n.asset_id for n in result.neighbours]


def test_own_preview_excluded_and_ranked(db):
    # Unlinked assets: "own" means the same seed artist and title.
    full = make_asset(db, seed_title="Seed")
    preview = make_asset(db, seed_title="Seed", kind=AudioKind.PREVIEW)
    near = make_asset(db, seed_title="Near")
    far = make_asset(db, seed_title="Far")
    embed(db, full, [1.0, 0.0])
    embed(db, preview, [1.0, 0.01])  # the closest of all, but the same seed
    embed(db, near, [0.9, 0.1])
    embed(db, far, [0.0, 1.0])

    result = similar_assets(db, full.id, "muq-mulan", k=10)

    assert result.embedded and names(result) == [near.id, far.id]
    similarities = [n.similarity for n in result.neighbours]
    assert similarities == sorted(similarities, reverse=True)
    assert similarities[0] == pytest.approx(0.9 / (0.81 + 0.01) ** 0.5, abs=1e-6)


def test_own_track_excluded_when_linked(db):
    from sidetrack.catalog import Album, Track

    album = Album(title="Album", artist_name="Broadcast")
    db.add(album)
    db.flush()
    track = Track(album_id=album.id, title="Seed", artist_name="Broadcast")
    db.add(track)
    db.flush()
    full = make_asset(db, track_id=track.id, seed_title="Seed")
    other_upload = make_asset(db, track_id=track.id, seed_title="Seed (live)")
    unlinked = make_asset(db, seed_title="Other")
    for asset, vector in ((full, [1.0, 0.0]), (other_upload, [1.0, 0.0]), (unlinked, [0.5, 0.5])):
        embed(db, asset, vector)

    assert names(similar_assets(db, full.id, "muq-mulan")) == [unlinked.id]


def test_other_models_and_revisions_ignored(db):
    query = make_asset(db, seed_title="Seed")
    current = make_asset(db, seed_title="Current")
    other_model = make_asset(db, seed_title="Other model")
    old_revision = make_asset(db, seed_title="Old revision")
    embed(db, query, [1.0, 0.0])
    embed(db, current, [0.0, 1.0])
    embed(db, other_model, [1.0, 0.0], model="muq")
    embed(db, old_revision, [1.0, 0.0], revision="0000000")

    assert names(similar_assets(db, query.id, "muq-mulan")) == [current.id]


def test_asset_not_embedded(db):
    asset = make_asset(db)
    stale = make_asset(db, seed_title="Stale")
    embed(db, stale, [1.0, 0.0], revision="0000000")

    for target in (asset, stale):
        result = similar_assets(db, target.id, "muq-mulan")
        assert not result.embedded and result.neighbours == []


def test_pruned_file_still_listed(db):
    query = make_asset(db, seed_title="Seed")
    pruned = make_asset(db, seed_title="Pruned", file_deleted_at=datetime.now(UTC))
    embed(db, query, [1.0, 0.0])
    embed(db, pruned, [0.8, 0.6])

    assert names(similar_assets(db, query.id, "muq-mulan")) == [pruned.id]


def test_k_limits_the_result(db):
    query = make_asset(db, seed_title="Seed")
    embed(db, query, [1.0, 0.0])
    for index in range(5):
        embed(db, make_asset(db, seed_title=f"Other {index}"), [1.0, float(index)])

    assert len(similar_assets(db, query.id, "muq-mulan", k=3).neighbours) == 3


# Operator commands


def settings(audio_dir: Path) -> Settings:
    return Settings(database_url="postgresql://unused", sidetrack_audio_dir=audio_dir)


def gpu_jobs(db):
    return db.scalars(select(BackgroundJob).where(BackgroundJob.task == TASK)).all()


def test_backfill_queues_only_assets_that_need_it(db, tmp_path):
    with_files = []
    for index in range(5):
        (tmp_path / f"{index}.wav").write_bytes(b"x")
        with_files.append(make_asset(db, path=f"{index}.wav", seed_title=f"Song {index}"))
    make_asset(db, path="gone.wav")  # no file on disk
    make_asset(db, path="0.wav", file_deleted_at=datetime.now(UTC))  # pruned
    for asset in with_files[:2]:
        embed(db, asset, [1.0, 0.0])
    embed(db, with_files[2], [1.0, 0.0], revision="0000000")  # stale: needs it again
    out = io.StringIO()

    code = main(["embed"], settings=settings(tmp_path), session=db, out=out)

    assert code == 0
    jobs = gpu_jobs(db)
    queued = [UUID(a) for j in jobs for a in db.scalar(_arguments(j))["asset_ids"]]
    assert sorted(queued) == sorted(a.id for a in with_files[2:])
    assert "Queued 3 assets for muq-mulan in 1 gpu jobs." in out.getvalue()
    assert all(str(j.id) in out.getvalue() for j in jobs)


def _arguments(job):
    return text(
        "SELECT args->'arguments' FROM job_queue.procrastinate_jobs WHERE id=:id"
    ).bindparams(id=job.queue_job_id)


def test_backfill_batches(db, tmp_path):
    from sidetrack.analysis.embeddings import queue_backfill

    for index in range(5):
        (tmp_path / f"{index}.wav").write_bytes(b"x")
        make_asset(db, path=f"{index}.wav", seed_title=f"Song {index}")

    backfill = queue_backfill(db, "muq-mulan", tmp_path, batch_size=2)

    assert backfill.assets == 5 and len(backfill.job_ids) == 3
    queues = (
        db.execute(
            text(
                "SELECT DISTINCT queue_name FROM job_queue.procrastinate_jobs WHERE id = ANY(:ids)"
            ),
            {"ids": [j.queue_job_id for j in gpu_jobs(db)]},
        )
        .scalars()
        .all()
    )
    assert queues == ["gpu"]


def test_asking_for_a_model_that_is_not_enabled(db, tmp_path, capsys):
    (tmp_path / "0.wav").write_bytes(b"x")
    make_asset(db, path="0.wav")

    assert main(["embed", "--model", "muq"], settings=settings(tmp_path), session=db) == 2

    assert "enabled: muq-mulan" in capsys.readouterr().err
    assert gpu_jobs(db) == []


def test_neighbours_command(db, tmp_path):
    query = make_asset(db, seed_artist="Broadcast", seed_title="Seed")
    near = make_asset(db, seed_artist="Stereolab", seed_title="Near")
    embed(db, query, [1.0, 0.0])
    embed(db, near, [0.6, 0.8])
    out = io.StringIO()

    assert main(["neighbours", query.sha256], settings=settings(tmp_path), session=db, out=out) == 0

    lines = out.getvalue().splitlines()
    assert lines[0] == "Broadcast - Seed (full), muq-mulan:"
    assert lines[1].startswith("  1. 0.600  Stereolab - Near (full)")


def test_nothing_schedules_embedding(db):
    seed_cleanup(db)
    scheduled = db.scalar(
        select(func.count()).select_from(JobSchedule).where(JobSchedule.task == TASK)
    )
    assert scheduled == 0
    for source in (ROOT / "sidetrack").rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        calls = {
            node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        }
        if "queue_backfill" in calls:
            assert source == ROOT / "sidetrack" / "audio.py", source
        if "JobSchedule" in calls:
            assert "embed" not in source.read_text(encoding="utf-8"), source
