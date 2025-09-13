import httpx
import pytest

from sidetrack.services.spotify import SpotifyService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_saved_tracks_stops_at_limit(respx_mock):
    first_page = {
        "items": [{"track": {"id": str(i)}} for i in range(50)],
        "next": f"{SpotifyService.api_root}/me/tracks?offset=50&limit=50",
    }
    second_page = {
        "items": [{"track": {"id": str(50 + i)}} for i in range(25)],
        "next": f"{SpotifyService.api_root}/me/tracks?offset=75&limit=50",
    }

    respx_mock.get(
        f"{SpotifyService.api_root}/me/tracks",
        params={"limit": "50", "offset": "0"},
    ).respond(200, json=first_page)
    respx_mock.get(
        f"{SpotifyService.api_root}/me/tracks",
        params={"limit": "25", "offset": "50"},
    ).respond(200, json=second_page)

    async with httpx.AsyncClient() as client:
        service = SpotifyService(client, access_token="token")
        items = await service.get_saved_tracks(limit=75)

    assert len(items) == 75
    assert respx_mock.calls.call_count == 2
