import copy

import pytest

from sidetrack.api import main as main_mod
from sidetrack.api.db import SessionLocal
from sidetrack.api.schemas.musicbrainz import MusicbrainzIngestResponse
from sidetrack.common.models import Artist, Release, Track

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


@pytest.fixture
def mb_client(client, monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=30):
        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return copy.deepcopy(sample_release)

        return Resp()

    monkeypatch.setattr(main_mod.HTTP_SESSION, "get", fake_get)
    monkeypatch.setattr(main_mod.time, "sleep", lambda x: None)
    return client


def test_ingest_musicbrainz_dedup(mb_client):
    resp = mb_client.post("/api/v1/ingest/musicbrainz", params={"release_mbid": "release-mbid"})
    assert resp.status_code == 200
    data = MusicbrainzIngestResponse.model_validate(resp.json())
    assert data.tracks >= 2

    session = SessionLocal()
    assert session.query(Artist).count() == 1
    assert session.query(Release).count() == 1
    assert session.query(Track).count() >= 2
    session.close()


def test_ingest_musicbrainz_not_found(mb_client, monkeypatch):
    class Resp:
        def raise_for_status(self):
            from requests import HTTPError, Response

            resp = Response()
            resp.status_code = 404
            raise HTTPError(response=resp)

        def json(self):
            return {}

    monkeypatch.setattr(main_mod.HTTP_SESSION, "get", lambda *a, **k: Resp())
    resp = mb_client.post("/api/v1/ingest/musicbrainz", params={"release_mbid": "missing"})
    assert resp.status_code == 404
