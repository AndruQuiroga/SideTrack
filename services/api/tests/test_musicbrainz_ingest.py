import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.api.app.schemas.musicbrainz import MusicbrainzIngestResponse

sample_release = {
    "id": "release-mbid",
    "title": "Sample Release",
    "date": "2020-01-01",
    "artist-credit": [{"artist": {"id": "artist-mbid", "name": "Test Artist"}}],
    "label-info": [{"label": {"name": "Test Label"}}],
    "media": [
        {
            "tracks": [
                {"recording": {"id": "track1", "title": "One", "length": 123000}},
                {"recording": {"id": "track2", "title": "Two", "length": 456000}},
            ]
        }
    ],
}


def _setup_app(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path}/test.db"
    monkeypatch.setenv("DATABASE_URL", db_url)
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    # Import after setting env so that the engine uses the test DB
    from services.api.app import main as main_mod
    from services.api.app.db import SessionLocal, get_db
    from services.api.app.main import app

    # override get_db dependency to return actual session (not contextmanager)
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # mock HTTP session .get
    def fake_get(url, params=None, headers=None, timeout=30):
        import copy

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return copy.deepcopy(sample_release)

        return Resp()

    monkeypatch.setattr(main_mod.HTTP_SESSION, "get", fake_get)
    monkeypatch.setattr(main_mod.time, "sleep", lambda x: None)
    return app, SessionLocal


@pytest.fixture
def mb_client(tmp_path, monkeypatch):
    app, SessionLocal = _setup_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        yield client, SessionLocal


def test_ingest_musicbrainz_dedup(mb_client):
    client, SessionLocal = mb_client
    resp = client.post("/ingest/musicbrainz", params={"release_mbid": "release-mbid"})
    assert resp.status_code == 200
    data = MusicbrainzIngestResponse.model_validate(resp.json())
    assert data.tracks >= 2

    session = SessionLocal()
    from services.common.models import Artist, Release, Track

    assert session.query(Artist).count() == 1
    assert session.query(Release).count() == 1
    assert session.query(Track).count() >= 2
    session.close()


def test_ingest_musicbrainz_not_found(mb_client, monkeypatch):
    client, _ = mb_client
    from services.api.app import main as main_mod

    class Resp:
        def raise_for_status(self):
            from requests import HTTPError, Response

            resp = Response()
            resp.status_code = 404
            raise HTTPError(response=resp)

        def json(self):
            return {}

    monkeypatch.setattr(main_mod.HTTP_SESSION, "get", lambda *a, **k: Resp())
    resp = client.post("/ingest/musicbrainz", params={"release_mbid": "missing"})
    assert resp.status_code == 404
