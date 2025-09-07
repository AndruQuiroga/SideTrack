import pytest
from sqlalchemy import select

from sidetrack.api.clients.spotify import SpotifyClient
from sidetrack.common.models import Listen, UserSettings

pytestmark = pytest.mark.asyncio


async def test_spotify_listens_ingest(async_client, async_session, monkeypatch):
    # create user settings with access token
    async_session.add(UserSettings(user_id="u1", spotify_access_token="tok"))
    await async_session.commit()

    async def fake_fetch(self, token, after=None, limit=50):
        return [
            {
                "track": {
                    "id": "sp1",
                    "name": "Song",
                    "artists": [{"name": "Artist"}],
                },
                "played_at": "2024-01-01T00:00:00.000Z",
            }
        ]

    monkeypatch.setattr(SpotifyClient, "fetch_recently_played", fake_fetch)

    r = await async_client.post("/api/v1/spotify/listens", headers={"X-User-Id": "u1"})
    assert r.status_code == 200
    assert r.json()["ingested"] == 1

    # second call should ingest nothing new
    r = await async_client.post("/api/v1/spotify/listens", headers={"X-User-Id": "u1"})
    assert r.status_code == 200
    assert r.json()["ingested"] == 0

    res = await async_session.execute(select(Listen))
    assert len(res.scalars().all()) == 1
