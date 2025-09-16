from datetime import datetime, timezone

import fakeredis.aioredis
import pytest
from fastapi_limiter import FastAPILimiter
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import sidetrack.api.main as api_main
from sidetrack.common.models import Artist, Listen, MBLabel, Release, Track


@pytest.mark.asyncio
@pytest.mark.contract
async def test_enrich_ids_endpoint_enriches_tracks(async_session, monkeypatch):
    artist = Artist(name="Artist")
    async_session.add(artist)
    await async_session.flush()

    release = Release(title="Album", artist_id=artist.artist_id)
    async_session.add(release)
    await async_session.flush()

    track = Track(title="Song", artist_id=artist.artist_id, release_id=release.release_id)
    async_session.add(track)
    await async_session.flush()

    listen = Listen(
        user_id="u1",
        track_id=track.track_id,
        played_at=datetime(2023, 6, 1, tzinfo=timezone.utc),
        source="test",
    )
    async_session.add(listen)
    await async_session.commit()

    class DummyMB:
        calls: list[tuple[str, str | None, str | None]] = []

        def __init__(self, client):
            self.client = client

        async def recording_by_isrc(self, isrc, title=None, artist=None):
            DummyMB.calls.append((isrc, title, artist))
            return {
                "recording_mbid": "rec-1",
                "artist_mbid": "art-1",
                "release_group_mbid": "rg-1",
                "label": "LabelCo",
                "year": 2005,
                "tags": [],
            }

    DummyMB.calls = []
    monkeypatch.setattr(api_main, "MusicBrainzService", DummyMB)

    async def override_get_db():
        yield async_session

    async def override_current_user():
        return "u1"

    async def noop_create_all():
        return None

    monkeypatch.setattr(api_main, "maybe_create_all", noop_create_all)

    app = api_main.app
    app.dependency_overrides[api_main.get_db] = override_get_db
    app.dependency_overrides[api_main.get_current_user] = override_current_user

    await FastAPILimiter.init(fakeredis.aioredis.FakeRedis())

    try:
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                resp = await client.post("/enrich/ids")
    finally:
        app.dependency_overrides.clear()
        await FastAPILimiter.close()

    assert resp.status_code == 200
    data = resp.json()
    assert data == {"detail": "ok", "processed": 1, "enriched": 1, "errors": []}

    assert DummyMB.calls == [(str(track.track_id), "Song", "Artist")]

    refreshed_track = await async_session.get(Track, track.track_id)
    assert refreshed_track.mbid == "rec-1"

    refreshed_artist = await async_session.get(Artist, artist.artist_id)
    assert refreshed_artist.mbid == "art-1"

    refreshed_release = await async_session.get(Release, release.release_id)
    assert refreshed_release.mbid == "rg-1"

    label = (
        await async_session.execute(select(MBLabel).where(MBLabel.track_id == track.track_id))
    ).scalar_one()
    assert label.primary_label == "LabelCo"
    assert label.era == "00s"
