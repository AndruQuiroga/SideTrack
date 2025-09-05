import os
import sys
from pathlib import Path
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

# Ensure repository root on sys.path and configure SQLite for tests
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from services.api.app.main import app  # noqa: E402
from services.api.app.db import SessionLocal, engine, get_db  # noqa: E402
from services.common.models import Base, Track, Artist, Listen, MoodScore  # noqa: E402
from services.api.app.constants import AXES, DEFAULT_METHOD  # noqa: E402

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
        db.query(MoodScore).delete()
        db.query(Listen).delete()
        db.query(Track).delete()
        db.query(Artist).delete()
        db.commit()


def _add_track(title: str, artist: str, value: float) -> int:
    """Create track with uniform mood scores and a listen."""
    with SessionLocal() as db:
        art = Artist(name=artist)
        db.add(art)
        db.commit()
        db.refresh(art)
        tr = Track(title=title, artist_id=art.artist_id)
        db.add(tr)
        db.commit()
        db.refresh(tr)
        db.add_all(
            [
                Listen(user_id="u1", track_id=tr.track_id, played_at=datetime.now(timezone.utc)),
                *[
                    MoodScore(
                        track_id=tr.track_id,
                        axis=ax,
                        method=DEFAULT_METHOD,
                        value=value,
                    )
                    for ax in AXES
                ],
            ]
        )
        db.commit()
        return tr.track_id


def test_outliers_endpoint_returns_sorted_tracks():
    _add_track("center", "a", 0.5)
    _add_track("near", "a", 0.6)
    far_tid = _add_track("far", "b", 0.0)

    resp = client.get("/dashboard/outliers", headers={"X-User-Id": "u1"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tracks"]) >= 3
    assert data["tracks"][0]["track_id"] == far_tid
    assert data["tracks"][0]["distance"] >= data["tracks"][1]["distance"]
