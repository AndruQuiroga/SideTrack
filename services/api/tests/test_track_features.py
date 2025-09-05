import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Setup env and path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from services.api.app.main import app  # noqa: E402
from services.api.app.db import SessionLocal, engine, get_db  # noqa: E402
from services.api.app.models import Base, Track, Feature, Embedding  # noqa: E402

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_db():
    with SessionLocal() as db:
        db.query(Embedding).delete()
        db.query(Feature).delete()
        db.query(Track).delete()
        db.commit()


def _create_track_with_features() -> int:
    with SessionLocal() as db:
        tr = Track(title="t")
        db.add(tr)
        db.flush()
        db.add(
            Feature(track_id=tr.track_id, bpm=120.0, pumpiness=0.5, percussive_harmonic_ratio=0.3)
        )
        db.add(Embedding(track_id=tr.track_id, model="m", dim=3, vector=[0.1, 0.2, 0.3]))
        db.commit()
        return tr.track_id


def test_get_track_features_returns_rows():
    tid = _create_track_with_features()
    resp = client.get(f"/tracks/{tid}/features")
    assert resp.status_code == 200
    data = resp.json()
    assert data["feature"]["bpm"] == 120.0
    assert data["embedding"]["model"] == "m"


def test_get_track_features_not_found():
    resp = client.get("/tracks/9999/features")
    assert resp.status_code == 404
