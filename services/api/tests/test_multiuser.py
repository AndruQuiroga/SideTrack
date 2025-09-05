import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

# Ensure repository root on sys.path and configure SQLite for tests
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from services.api.app import main  # noqa: E402
from services.api.app.constants import DEFAULT_METHOD  # noqa: E402
from services.api.app.db import SessionLocal, engine, get_db  # noqa: E402
from services.api.app.main import app  # noqa: E402
from services.common.models import Base, Listen, MoodAggWeek, MoodScore, Track  # noqa: E402

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
        db.query(MoodAggWeek).delete()
        db.query(MoodScore).delete()
        db.query(Listen).delete()
        db.query(Track).delete()
        db.commit()


def _add_listen(user: str, value: float):
    with SessionLocal() as db:
        tr = Track(title=f"t-{user}")
        db.add(tr)
        db.commit()
        db.refresh(tr)
        db.add_all(
            [
                Listen(
                    user_id=user, track_id=tr.track_id, played_at=datetime(2024, 1, 1, tzinfo=UTC)
                ),
                MoodScore(track_id=tr.track_id, axis="energy", method=DEFAULT_METHOD, value=value),
            ]
        )
        db.commit()
        return tr.track_id


def test_aggregate_weeks_is_scoped_to_user(monkeypatch):
    monkeypatch.setattr(main, "score_track", lambda track_id, method=DEFAULT_METHOD, db=None: None)
    _add_listen("u1", 0.7)
    _add_listen("u2", 0.3)

    r1 = client.post("/aggregate/weeks", headers={"X-User-Id": "u1"})
    assert r1.status_code == 200
    r2 = client.post("/aggregate/weeks", headers={"X-User-Id": "u2"})
    assert r2.status_code == 200

    with SessionLocal() as db:
        rows = db.execute(select(MoodAggWeek)).all()
        assert len(rows) == 2
        m1 = db.execute(select(MoodAggWeek).where(MoodAggWeek.user_id == "u1")).scalar_one()
        m2 = db.execute(select(MoodAggWeek).where(MoodAggWeek.user_id == "u2")).scalar_one()
        assert m1.mean == pytest.approx(0.7)
        assert m2.mean == pytest.approx(0.3)

    t_resp = client.get("/dashboard/trajectory", headers={"X-User-Id": "u1"})
    assert t_resp.status_code == 200
    t_data = t_resp.json()
    assert len(t_data["points"]) == 1
    assert t_data["points"][0]["y"] == pytest.approx(0.7)
