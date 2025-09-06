from rq import Queue

from sidetrack.api.db import SessionLocal
from sidetrack.api.schemas.tracks import AnalyzeTrackResponse
from sidetrack.common.models import Track


def test_analyze_track_schedules_job(client, redis_conn):
    with SessionLocal() as db:
        tr = Track(title="test", path_local="song.mp3")
        db.add(tr)
        db.commit()
        tid = tr.track_id
    resp = client.post(f"/analyze/track/{tid}")
    assert resp.status_code == 200
    data = AnalyzeTrackResponse.model_validate(resp.json())
    assert data.status == "scheduled"
    q = Queue("analysis", connection=redis_conn)
    jobs = q.jobs
    assert jobs and jobs[0].args[0] == tid


def test_analyze_track_not_found(client):
    resp = client.post("/analyze/track/9999")
    assert resp.status_code == 404


def test_analyze_track_missing_path(client):
    with SessionLocal() as db:
        tr = Track(title="nop")
        db.add(tr)
        db.commit()
        tid = tr.track_id
    resp = client.post(f"/analyze/track/{tid}")
    assert resp.status_code == 400
