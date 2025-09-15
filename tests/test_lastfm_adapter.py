import httpx
import pytest
from pytest_socket import enable_socket

from sidetrack.enrichment.lastfm import LastfmAdapter

enable_socket()


@pytest.mark.asyncio
async def test_get_recent_tracks_returns_track_refs():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["method"] == "user.getrecenttracks"
        payload = {
            "recenttracks": {
                "track": [
                    {
                        "name": "Song",
                        "artist": {"name": "Artist"},
                        "mbid": "track-mbid",
                    }
                ]
            }
        }
        return httpx.Response(200, json=payload, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = LastfmAdapter("key", client=client)
        tracks = await adapter.get_recent_tracks("user", limit=1)

    assert len(tracks) == 1
    assert tracks[0].title == "Song"
    assert tracks[0].artists == ["Artist"]
    assert tracks[0].lastfm_mbid == "track-mbid"


@pytest.mark.asyncio
async def test_get_tags_returns_names():
    def handler(request: httpx.Request) -> httpx.Response:
        method = request.url.params["method"]
        assert method in {"artist.gettoptags", "track.gettoptags"}
        payload = {
            "toptags": {
                "tag": [
                    {"name": "rock", "count": "10"},
                    {"name": "pop", "count": "5"},
                    "unexpected",
                ]
            }
        }
        return httpx.Response(200, json=payload, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = LastfmAdapter("key", client=client)
        tags = await adapter.get_tags("Some Artist", track="Track")

    assert tags == ["rock", "pop"]
