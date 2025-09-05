import os
import sys
from pathlib import Path

# Configure database before importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_api.db")
os.environ.setdefault("AUTO_MIGRATE", "1")

sys.path.append(str(Path(__file__).resolve().parents[3]))

import fakeredis
from fastapi.testclient import TestClient
from rq import Queue

from services.api.app import main as app_main
from services.api.app.db import SessionLocal, maybe_create_all
from services.common.models import Track

# Ensure tables exist
maybe_create_all()


def test_analyze_track_schedules_job():
    connection = fakeredis.FakeRedis()
    app_main._REDIS_CONN = connection
    with SessionLocal() as db:
        tr = Track(title="test", path_local="song.mp3")
        db.add(tr)
        db.commit()
        tid = tr.track_id
    with TestClient(app_main.app) as client:
        resp = client.post(f"/analyze/track/{tid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "scheduled"
    q = Queue("analysis", connection=connection)
    jobs = q.jobs
    assert jobs and jobs[0].args[0] == tid


def test_analyze_track_not_found():
    with TestClient(app_main.app) as client:
        resp = client.post("/analyze/track/9999")
        assert resp.status_code == 404


def test_analyze_track_missing_path():
    connection = fakeredis.FakeRedis()
    app_main._REDIS_CONN = connection
    with SessionLocal() as db:
        tr = Track(title="nop")
        db.add(tr)
        db.commit()
        tid = tr.track_id
    with TestClient(app_main.app) as client:
        resp = client.post(f"/analyze/track/{tid}")
        assert resp.status_code == 400
