import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

# Ensure repository root on sys.path and configure SQLite for tests
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from services.api.app.main import app  # noqa: E402  (import after setting env)
from services.api.app.db import SessionLocal, engine, get_db  # noqa: E402
from services.api.app.models import Base, Track, UserLabel  # noqa: E402


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
    """Clear tables between tests."""
    with SessionLocal() as db:
        db.query(UserLabel).delete()
        db.query(Track).delete()
        db.commit()


def _create_track() -> int:
    with SessionLocal() as db:
        tr = Track(title="test")
        db.add(tr)
        db.commit()
        db.refresh(tr)
        return tr.track_id


def test_submit_label_stores_label():
    tid = _create_track()
    resp = client.post(
        "/labels",
        params={"track_id": tid, "axis": "energy", "value": 0.5},
        headers={"X-User-Id": "u1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["detail"] == "accepted"
    assert data["axis"] == "energy"

    with SessionLocal() as db:
        lbl = db.execute(select(UserLabel)).scalar_one()
        assert lbl.user_id == "u1"
        assert lbl.axis == "energy"
        assert lbl.value == 0.5


def test_submit_label_rejects_unknown_axis():
    tid = _create_track()
    resp = client.post(
        "/labels",
        params={"track_id": tid, "axis": "invalid", "value": 0.5},
        headers={"X-User-Id": "u1"},
    )
    assert resp.status_code == 400
    with SessionLocal() as db:
        assert db.execute(select(UserLabel)).first() is None

