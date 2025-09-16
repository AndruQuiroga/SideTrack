import httpx
import pytest

from sidetrack.services.spotify import SpotifyUserClient


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_saved_tracks_stops_at_limit(respx_mock):
    first_page = {
        "items": [{"track": {"id": str(i)}} for i in range(50)],
        "next": f"{SpotifyUserClient.api_root}/me/tracks?offset=50&limit=50",
    }
    second_page = {
        "items": [{"track": {"id": str(50 + i)}} for i in range(25)],
        "next": f"{SpotifyUserClient.api_root}/me/tracks?offset=75&limit=50",
    }

    respx_mock.get(
        f"{SpotifyUserClient.api_root}/me/tracks",
        params={"limit": "50", "offset": "0"},
    ).respond(200, json=first_page)
    respx_mock.get(
        f"{SpotifyUserClient.api_root}/me/tracks",
        params={"limit": "25", "offset": "50"},
    ).respond(200, json=second_page)

    async with httpx.AsyncClient() as client:
        service = SpotifyUserClient(client, access_token="token")
        items = await service.get_saved_tracks(limit=75)

    assert len(items) == 75
    assert respx_mock.calls.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_spotify_user_client_refreshes_tokens(respx_mock):
    me_route = respx_mock.get(f"{SpotifyUserClient.api_root}/me")
    me_route.side_effect = [
        httpx.Response(401, json={"error": {"status": 401, "message": "expired"}}),
        httpx.Response(200, json={"id": "user"}),
    ]

    refresh_route = respx_mock.post(
        f"{SpotifyUserClient.auth_root}/api/token",
    ).respond(
        200,
        json={"access_token": "new-access", "refresh_token": "new-refresh"},
    )

    async with httpx.AsyncClient() as client:
        service = SpotifyUserClient(
            client,
            access_token="expired",
            client_id="cid",
            client_secret="secret",
            refresh_token="refresh-token",
        )

        result = await service.get_current_user()

        assert result == {"id": "user"}
        assert service.access_token == "new-access"
        assert service.refresh_token == "new-refresh"
        assert me_route.call_count == 2
        assert refresh_route.called
