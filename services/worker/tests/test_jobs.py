import os

import fakeredis
import numpy as np
import soundfile as sf
from rq import Queue, SimpleWorker

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_worker.db")
os.environ.setdefault("AUTO_MIGRATE", "1")

from services.api.app.db import SessionLocal, maybe_create_all
from services.worker.worker.jobs import analyze_track, compute_embeddings

from services.common.models import Feature, Track

maybe_create_all()


def test_jobs_are_executed():
    """Jobs enqueued on RQ queues should be picked up and executed."""
    connection = fakeredis.FakeRedis()

    with SessionLocal() as db:
        audio_path = "test_worker.wav"
        sf.write(audio_path, np.zeros(1024), 22050)
        tr = Track(title="t", path_local=audio_path)
        db.add(tr)
        db.commit()
        track_id = tr.track_id

    analysis_q = Queue("analysis", connection=connection)
    scoring_q = Queue("scoring", connection=connection)

    job1 = analysis_q.enqueue(analyze_track, track_id)
    job2 = scoring_q.enqueue(compute_embeddings, [1.0, 2.0, 3.0])

    worker = SimpleWorker([analysis_q, scoring_q], connection=connection)
    worker.work(burst=True)

    with SessionLocal() as db:
        feat = db.get(Feature, job1.result)
        assert feat and feat.track_id == track_id

    assert job2.result == [round(x, 4) for x in [1 / 3, 2 / 3, 1.0]]
