import pytest
from sqlalchemy import select

from sidetrack.services.spotify import SpotifyClient
from sidetrack.common.models import Feature, UserSettings
from tests.factories import TrackFactory

pytestmark = pytest.mark.asyncio


async def test_spotify_feature_backfill(async_client, async_session, monkeypatch):
    track = TrackFactory(spotify_id="sp123")
    async_session.add_all([track, UserSettings(user_id="u1", spotify_access_token="tok")])
    await async_session.flush()
    tid = track.track_id
    await async_session.commit()

    async def fake_audio_features(self, token, sid):
        assert token == "tok"
        assert sid == "sp123"
        return {"tempo": 100.0, "key": 5, "mode": 1, "energy": 0.8}

    monkeypatch.setattr(SpotifyClient, "get_audio_features", fake_audio_features)

    r = await async_client.post(f"/api/v1/spotify/features/{tid}", headers={"X-User-Id": "u1"})
    assert r.status_code == 200
    assert r.json()["status"] == "created"

    res = await async_session.execute(select(Feature).where(Feature.track_id == tid))
    feat = res.scalar_one()
    assert feat.bpm == 100.0
    assert feat.pumpiness == 0.8
    assert feat.key == "F major"

    # second call should detect existing feature
    r = await async_client.post(f"/api/v1/spotify/features/{tid}", headers={"X-User-Id": "u1"})
    assert r.status_code == 200
    assert r.json()["status"] == "exists"


async def test_spotify_feature_batch(async_client, async_session, monkeypatch):
    t1 = TrackFactory(spotify_id="a1")
    t2 = TrackFactory(spotify_id="a2")
    async_session.add_all([t1, t2, UserSettings(user_id="u1", spotify_access_token="tok")])
    await async_session.flush()
    t1_id, t2_id = t1.track_id, t2.track_id
    await async_session.commit()

    calls: list[str] = []

    async def fake_audio_features(self, token, sid):
        calls.append(sid)
        return {"tempo": 90.0, "key": 0, "mode": 1, "energy": 0.5}

    monkeypatch.setattr(SpotifyClient, "get_audio_features", fake_audio_features)

    r = await async_client.post("/api/v1/spotify/features/backfill", headers={"X-User-Id": "u1"})
    assert r.status_code == 200
    assert r.json()["backfilled"] == 2
    assert set(calls) == {"a1", "a2"}

    res = await async_session.execute(select(Feature).where(Feature.track_id.in_([t1_id, t2_id])))
    assert len(res.scalars().all()) == 2
