import numpy as np
import pytest
import soundfile as sf
from rq import Queue, SimpleWorker

from sidetrack.api.db import SessionLocal
from sidetrack.common.models import Feature
from sidetrack.worker.jobs import analyze_track, compute_embeddings
from tests.factories import TrackFactory

pytestmark = pytest.mark.integration


def test_jobs_are_executed(redis_conn, tmp_path):
    """Jobs enqueued on RQ queues should be picked up and executed."""
    audio_path = tmp_path / "test_worker.wav"
    sf.write(audio_path, np.zeros(1024), 22050)

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

    job1 = analysis_q.enqueue(analyze_track, track_id)
    job2 = scoring_q.enqueue(compute_embeddings, [1.0, 2.0, 3.0])

    worker = SimpleWorker([analysis_q, scoring_q], connection=redis_conn)
    worker.work(burst=True)

    with SessionLocal() as db:
        feat = db.get(Feature, job1.result)
        assert feat and feat.track_id == track_id

    assert job2.result == [round(x, 4) for x in [1 / 3, 2 / 3, 1.0]]
