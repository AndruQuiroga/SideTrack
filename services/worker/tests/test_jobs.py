import sys
from pathlib import Path

import fakeredis
from rq import Queue, SimpleWorker

# Make the worker package importable when tests are executed from the repo root
sys.path.append(str(Path(__file__).resolve().parents[1]))
from worker.jobs import analyze_track, compute_embeddings


def test_jobs_are_executed():
    """Jobs enqueued on RQ queues should be picked up and executed."""
    connection = fakeredis.FakeRedis()

    analysis_q = Queue("analysis", connection=connection)
    scoring_q = Queue("scoring", connection=connection)

    job1 = analysis_q.enqueue(analyze_track, "42")
    job2 = scoring_q.enqueue(compute_embeddings, [1.0, 2.0, 3.0])

    worker = SimpleWorker([analysis_q, scoring_q], connection=connection)
    worker.work(burst=True)

    assert job1.result == "analysis-complete:42"
    assert job2.result == [round(x, 4) for x in [1/3, 2/3, 1.0]]
