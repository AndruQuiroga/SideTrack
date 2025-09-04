import os
import sys

# Configure database before importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_api.db")
os.environ.setdefault("AUTO_MIGRATE", "1")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app, ANALYSIS_QUEUE
from app.db import SessionLocal, maybe_create_all
from app.models import Track

# Ensure tables exist
maybe_create_all()


def test_analyze_track_schedules_job():
    ANALYSIS_QUEUE.clear()
    with SessionLocal() as db:
        tr = Track(title="test", path_local="song.mp3")
        db.add(tr)
        db.commit()
        tid = tr.track_id
    with TestClient(app) as client:
        resp = client.post(f"/analyze/track/{tid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "scheduled"
    assert tid in ANALYSIS_QUEUE


def test_analyze_track_not_found():
    with TestClient(app) as client:
        resp = client.post("/analyze/track/9999")
        assert resp.status_code == 404


def test_analyze_track_missing_path():
    ANALYSIS_QUEUE.clear()
    with SessionLocal() as db:
        tr = Track(title="nop")
        db.add(tr)
        db.commit()
        tid = tr.track_id
    with TestClient(app) as client:
        resp = client.post(f"/analyze/track/{tid}")
        assert resp.status_code == 400
