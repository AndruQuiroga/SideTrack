import pytest
from sqlalchemy import select

from sidetrack.api.clients import spotify as spotify_module
from sidetrack.common.models import Listen, Track


@pytest.mark.asyncio
async def test_import_spotify_listens(async_client, async_session, monkeypatch):
    monkeypatch.setenv("SPOTIFY_TOKEN", "tok")

    sample = [
        {
            "track": {
                "id": "s1",
                "name": "Song",
                "artists": [{"name": "Artist"}],
                "duration_ms": 60000,
            },
            "played_at": "2024-01-01T00:00:00Z",
        }
    ]

    async def fake_fetch(self, token, after=None, limit=50):
        assert token == "tok"
        return sample

    monkeypatch.setattr(
        spotify_module.SpotifyClient, "fetch_recently_played", fake_fetch
    )

    resp = await async_client.post(
        "/api/v1/spotify/listens", headers={"X-User-Id": "user1"}
    )
    assert resp.status_code == 200
    assert resp.json()["ingested"] == 1

    listens = (await async_session.execute(select(Listen))).scalars().all()
    assert len(listens) == 1
    tracks = (await async_session.execute(select(Track))).scalars().all()
    assert tracks[0].spotify_id == "s1"
