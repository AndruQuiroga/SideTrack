from datetime import UTC, datetime

import pytest

from sidetrack.common.models import Artist, Listen, Track

pytestmark = pytest.mark.asyncio


async def test_recent_listens_endpoint(async_client, async_session):
    artist = Artist(name="Artist")
    track = Track(title="Song", artist=artist)
    async_session.add_all([artist, track])
    await async_session.flush()
    track_id = track.track_id

    l1 = Listen(user_id="u1", track_id=track_id, played_at=datetime(2024, 1, 1, tzinfo=UTC))
    l2 = Listen(user_id="u1", track_id=track_id, played_at=datetime(2024, 1, 2, tzinfo=UTC))
    async_session.add_all([l1, l2])
    await async_session.commit()

    resp = await async_client.get("/api/v1/listens/recent?limit=1", headers={"X-User-Id": "u1"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["listens"]) == 1
    item = data["listens"][0]
    assert item["track_id"] == track_id
    assert item["title"] == "Song"
    assert item["artist"] == "Artist"
    assert item["played_at"].startswith("2024-01-02")
