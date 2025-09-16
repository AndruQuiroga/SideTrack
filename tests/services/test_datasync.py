from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import select

from sidetrack.api.config import Settings
from sidetrack.api.repositories.artist_repository import ArtistRepository
from sidetrack.api.repositories.listen_repository import ListenRepository
from sidetrack.api.repositories.release_repository import ReleaseRepository
from sidetrack.api.repositories.track_repository import TrackRepository
from sidetrack.services.listens import ListenService
from sidetrack.services.lastfm import LastfmClient
from sidetrack.common.models import (
    Artist,
    Listen,
    MBLabel,
    MBTag,
    MusicBrainzRecording,
    Release,
    Track,
    UserSettings,
)
from sidetrack.services.datasync import enrich_ids, sync_user
from sidetrack.services.listenbrainz import ListenBrainzClient
from sidetrack.services.musicbrainz import MusicBrainzService
from sidetrack.services.spotify import SpotifyClient


@pytest.mark.asyncio
async def test_sync_user_triggers_enrichment(async_session, monkeypatch):
    async_session.add(UserSettings(user_id="u1", spotify_access_token="tok"))
    await async_session.commit()

    sp_client = SpotifyClient(httpx.AsyncClient())
    async def fake_fetch(token, after=None):
        return [
            {
                "track": {"id": "sp1", "name": "Song", "artists": [{"name": "Artist"}]},
                "played_at": "2024-01-01T00:00:00.000Z",
            }
        ]
    monkeypatch.setattr(sp_client, "fetch_recently_played", fake_fetch)

    lf_client = LastfmClient(httpx.AsyncClient(), api_key="k", api_secret="s")
    lf_calls = {}
    async def fake_tags(db, track_id, artist, track):
        lf_calls[track_id] = (artist, track)
        return {}
    monkeypatch.setattr(lf_client, "get_track_tags", fake_tags)

    lb_client = ListenBrainzClient(httpx.AsyncClient())

    mb_service = MusicBrainzService(httpx.AsyncClient())
    mb_calls = {}
    async def fake_mb(isrc, title=None, artist=None, recording_mbid=None):
        mb_calls[isrc] = (title, artist)
        return {}
    monkeypatch.setattr(mb_service, "recording_by_isrc", fake_mb)

    listen_service = ListenService(
        ArtistRepository(async_session),
        ReleaseRepository(async_session),
        TrackRepository(async_session),
        ListenRepository(async_session),
    )

    settings = Settings()
    res = await sync_user(
        "u1",
        db=async_session,
        listen_service=listen_service,
        clients=[sp_client, lf_client, lb_client],
        mb_service=mb_service,
        settings=settings,
    )

    assert res["ingested"] == 1
    assert lf_calls
    assert mb_calls


@pytest.mark.asyncio
@pytest.mark.unit
async def test_enrich_ids_persists_metadata(async_session):
    artist = Artist(name="Artist")
    async_session.add(artist)
    await async_session.flush()

    release = Release(title="Album", artist_id=artist.artist_id)
    async_session.add(release)
    await async_session.flush()

    track = Track(
        title="Song",
        artist_id=artist.artist_id,
        release_id=release.release_id,
        isrc="US1234567890",
    )
    async_session.add(track)
    await async_session.flush()

    listen = Listen(
        user_id="u1",
        track_id=track.track_id,
        played_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        source="test",
    )
    async_session.add(listen)
    await async_session.commit()

    class StubMB:
        calls: list[tuple[str | None, str | None, str | None, str | None]] = []

        async def recording_by_isrc(self, isrc, title=None, artist=None, recording_mbid=None):
            StubMB.calls.append((isrc, title, artist, recording_mbid))
            return {
                "recording_mbid": "rec-1",
                "artist_mbid": "art-1",
                "release_group_mbid": "rg-1",
                "label": "LabelCo",
                "year": 2016,
                "tags": ["Rock", "Dream-Pop"],
                "isrc": isrc,
            }

    result = await enrich_ids("u1", db=async_session, mb_service=StubMB())

    assert result.processed == 1
    assert result.enriched == 1
    assert result.errors == []
    assert StubMB.calls == [("US1234567890", "Song", "Artist", None)]

    refreshed_track = await async_session.get(Track, track.track_id)
    assert refreshed_track.mbid == "rec-1"
    assert refreshed_track.isrc == "US1234567890"

    refreshed_artist = await async_session.get(Artist, artist.artist_id)
    assert refreshed_artist.mbid == "art-1"

    refreshed_release = await async_session.get(Release, release.release_id)
    assert refreshed_release.mbid == "rg-1"

    label = (
        await async_session.execute(select(MBLabel).where(MBLabel.track_id == track.track_id))
    ).scalar_one()
    assert label.primary_label == "LabelCo"
    assert label.era == "10s"

    tags = (
        await async_session.execute(select(MBTag).where(MBTag.track_id == track.track_id))
    ).scalars().all()
    assert {tag.tag for tag in tags} == {"rock", "dream pop"}
    assert all(tag.score == 1.0 for tag in tags)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_enrich_ids_collects_errors(async_session):
    artist = Artist(name="Artist")
    async_session.add(artist)
    await async_session.flush()

    track = Track(title="Song", artist_id=artist.artist_id)
    async_session.add(track)
    await async_session.flush()

    listen = Listen(
        user_id="u1",
        track_id=track.track_id,
        played_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        source="test",
    )
    async_session.add(listen)
    await async_session.commit()

    class FailingMB:
        async def recording_by_isrc(self, isrc, title=None, artist=None, recording_mbid=None):
            raise RuntimeError("boom")

    result = await enrich_ids("u1", db=async_session, mb_service=FailingMB())

    assert result.processed == 1
    assert result.enriched == 0
    assert result.errors == [{"track_id": str(track.track_id), "error": "boom"}]

    refreshed_track = await async_session.get(Track, track.track_id)
    assert refreshed_track.mbid is None

    label = (
        await async_session.execute(select(MBLabel).where(MBLabel.track_id == track.track_id))
    ).scalar_one_or_none()
    assert label is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_enrich_ids_updates_mb_recording(async_session, monkeypatch):
    artist = Artist(name="Artist")
    async_session.add(artist)
    await async_session.flush()

    track = Track(title="Song", artist_id=artist.artist_id, isrc="US1111111111")
    async_session.add(track)
    await async_session.flush()

    listen = Listen(
        user_id="u1",
        track_id=track.track_id,
        played_at=datetime(2024, 2, 1, tzinfo=timezone.utc),
        source="test",
    )
    async_session.add(listen)
    await async_session.commit()

    payload = {
        "isrc": "US1111111111",
        "recordings": [
            {
                "id": "rec-2",
                "title": "Song",
                "artist-credit": [{"artist": {"id": "art-2", "name": "Artist"}}],
                "releases": [
                    {
                        "date": "2012-03-01",
                        "label-info": [{"label": {"name": "Another Label"}}],
                        "release-group": {"id": "rg-2"},
                    }
                ],
                "tags": [{"name": "Electronic"}],
                "isrcs": ["US1111111111"],
            }
        ],
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        if "isrc" in str(request.url):
            return httpx.Response(200, json=payload)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        mb_service = MusicBrainzService(client, db=async_session)
        result = await enrich_ids("u1", db=async_session, mb_service=mb_service)

    assert result.processed == 1
    assert result.enriched == 1
    record = await async_session.get(MusicBrainzRecording, "US1111111111")
    assert record is not None
    assert record.recording_mbid == "rec-2"
    assert record.artist_mbid == "art-2"
    assert record.release_group_mbid == "rg-2"
    assert record.label == "Another Label"
    assert record.tags == ["Electronic"]
