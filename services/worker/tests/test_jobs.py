import numpy as np
import pytest
import soundfile as sf
from rq import Queue, SimpleWorker

from sidetrack.api.db import SessionLocal
from sidetrack.common.models import Feature
from sidetrack.config import ExtractionConfig
from sidetrack.extraction.pipeline import analyze_track
from sidetrack.worker.jobs import compute_embeddings
from tests.factories import TrackFactory

pytestmark = pytest.mark.integration


def test_jobs_are_executed(redis_conn, tmp_path):
    """Jobs enqueued on RQ queues should be picked up and executed."""
    audio_path = tmp_path / "test_worker.wav"
    data = np.array([0.0, 1.0, 2.0, 3.0])
    sr = 22050
    sf.write(audio_path, data, sr)
    y, sr = sf.read(audio_path)

    with SessionLocal() as db:
        from sidetrack.common.models import Base

        Base.metadata.create_all(db.bind)
        tr = TrackFactory(title="t", path_local=str(audio_path))
        db.add(tr)
        db.flush()
        track_id = tr.track_id
        db.commit()

    analysis_q = Queue("analysis", connection=redis_conn)
    scoring_q = Queue("scoring", connection=redis_conn)

    cfg = ExtractionConfig()
    job1 = analysis_q.enqueue(analyze_track, track_id, cfg)
    job2 = scoring_q.enqueue(compute_embeddings, track_id, y, sr, cfg)

    worker = SimpleWorker([analysis_q, scoring_q], connection=redis_conn)
    worker.work(burst=True)

    with SessionLocal() as db:
        feat = db.get(Feature, job1.result)
        assert feat and feat.track_id == track_id

    mean = float(np.mean(y))
    std = float(np.std(y))
    max_val = max(abs(mean), abs(std)) or 1.0
    expected = [round(mean / max_val, 4), round(std / max_val, 4)]
    assert job2.result == {"openl3": expected}
