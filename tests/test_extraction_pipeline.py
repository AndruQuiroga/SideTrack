import numpy as np
import soundfile as sf
import pytest
from sqlalchemy import select

from sidetrack.common.models import Feature, Embedding
from sidetrack.config.extraction import ExtractionConfig
from sidetrack.extraction.pipeline import analyze_tracks
from tests.factories import TrackFactory

pytestmark = pytest.mark.unit


def test_pipeline_extracts_and_upserts(session, redis_conn, tmp_path):
    sr = 22050
    t = np.linspace(0, 1, sr, False)
    y = np.sin(2 * np.pi * 440 * t)
    path = tmp_path / "tone.wav"
    sf.write(path, y, sr)

    tr = TrackFactory(path_local=str(path))
    session.add(tr)
    session.flush()
    tid = tr.track_id
    session.commit()

    cfg = ExtractionConfig()
    cfg.set_seed(0)
    analyze_tracks(session, [tid], cfg, redis_conn)

    feat = session.execute(select(Feature).where(Feature.track_id == tid)).scalar_one()
    assert feat.dataset_version == cfg.dataset_version
    emb = session.execute(select(Embedding).where(Embedding.track_id == tid)).scalar_one()
    assert emb.model == cfg.embedding_model

    # run again to ensure upsert
    analyze_tracks(session, [tid], cfg, redis_conn)
    feats = session.execute(select(Feature).where(Feature.track_id == tid)).scalars().all()
    assert len(feats) == 1
    embs = session.execute(select(Embedding).where(Embedding.track_id == tid)).scalars().all()
    assert len(embs) == 1

    key = f"emb:{cfg.embedding_model}:{tid}:{cfg.dataset_version}"
    assert redis_conn.get(key) is not None
