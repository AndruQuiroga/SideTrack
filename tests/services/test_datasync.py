import httpx
import pytest

from sidetrack.api.config import Settings
from sidetrack.api.repositories.artist_repository import ArtistRepository
from sidetrack.api.repositories.listen_repository import ListenRepository
from sidetrack.api.repositories.release_repository import ReleaseRepository
from sidetrack.api.repositories.track_repository import TrackRepository
from sidetrack.services.listens import ListenService
from sidetrack.api.clients.lastfm import LastfmClient
from sidetrack.common.models import UserSettings
from sidetrack.services.datasync import sync_user
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
    async def fake_mb(isrc, title=None, artist=None):
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
