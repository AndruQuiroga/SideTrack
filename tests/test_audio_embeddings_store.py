"""Spec: analysis/audio-embeddings: storage per asset and model, and the asset's lifetime."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from sidetrack.analysis.models import AudioAsset, AudioEmbedding
from sidetrack.types import AudioKind, AudioSource, AudioVerification

pytestmark = pytest.mark.unit


def make_asset(db, **overrides) -> AudioAsset:
    values = {
        "sha256": uuid4().hex + uuid4().hex,
        "seed_artist": "Broadcast",
        "seed_title": "Come On Let's Go",
        "source": AudioSource.YOUTUBE_MUSIC,
        "source_ref": uuid4().hex,
        "kind": AudioKind.FULL,
        "path": "x.webm",
        "format": "webm",
        "verification": AudioVerification.UNVERIFIED,
        "fetched_at": datetime.now(UTC),
    }
    asset = AudioAsset(**{**values, **overrides})
    db.add(asset)
    db.flush()
    return asset


def embedding(asset, vector, *, dim=None, model="muq-mulan") -> AudioEmbedding:
    return AudioEmbedding(
        asset_id=asset.id,
        model=model,
        checkpoint_revision="rev",
        pipeline="test",
        dim=len(vector) if dim is None else dim,
        embedding=vector,
    )


def test_embedding_round_trips_with_provenance(db):
    asset = make_asset(db)
    db.add(embedding(asset, [0.6, 0.8, 0.0]))
    db.flush()

    row = db.scalar(select(AudioEmbedding).where(AudioEmbedding.asset_id == asset.id))
    assert list(row.embedding) == pytest.approx([0.6, 0.8, 0.0])
    assert (row.model, row.checkpoint_revision, row.pipeline, row.dim) == (
        "muq-mulan",
        "rev",
        "test",
        3,
    )
    assert row.embedded_at is not None


def test_wrong_dimension_is_rejected(db):
    asset = make_asset(db)
    with pytest.raises(IntegrityError, match="ck_audio_embeddings_dim"):
        with db.begin_nested():
            db.add(embedding(asset, [0.6, 0.8, 0.0], dim=512))
            db.flush()
    assert db.scalar(select(AudioEmbedding).where(AudioEmbedding.asset_id == asset.id)) is None


def test_one_embedding_per_asset_and_model(db):
    asset = make_asset(db)
    db.add(embedding(asset, [1.0, 0.0]))
    db.add(embedding(asset, [0.0, 1.0, 0.0], model="muq"))  # another model is fine
    db.flush()
    with pytest.raises(IntegrityError, match="uq_audio_embeddings_asset_model"):
        with db.begin_nested():
            db.add(embedding(asset, [0.0, 1.0]))
            db.flush()


def test_deleting_an_asset_deletes_its_embeddings(db):
    asset = make_asset(db)
    db.add(embedding(asset, [1.0, 0.0]))
    db.flush()

    db.execute(delete(AudioAsset).where(AudioAsset.id == asset.id))
    db.flush()

    assert db.scalar(select(AudioEmbedding).where(AudioEmbedding.asset_id == asset.id)) is None
