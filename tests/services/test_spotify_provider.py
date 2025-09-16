from datetime import datetime, timezone

import httpx
import pytest

from sidetrack.services.providers.spotify import SpotifyIngester
from sidetrack.services.spotify import SpotifyClient


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_recent_includes_auth_token(respx_mock):
    payload = {
        "played_at": "2024-01-01T00:00:00.000Z",
        "track": {
            "name": "Song A",
            "artists": [{"name": "Artist A"}],
        },
    }

    route = respx_mock.get(
        f"{SpotifyClient.api_root}/me/player/recently-played",
        params={"limit": "2"},
    ).mock(return_value=httpx.Response(200, json={"items": [payload]}))

    ingester = SpotifyIngester(page_size=2)
    listens = await ingester.fetch_recent("oauth-token", user_id="alice")

    assert route.called
    request = route.calls[0].request
    assert request.headers["Authorization"] == "Bearer oauth-token"
    assert listens[0]["user_name"] == "alice"
    assert listens[0]["track_metadata"]["track_name"] == "Song A"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_recent_filters_since_and_paginates(respx_mock):
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    first_times = [base.replace(minute=5), base.replace(minute=4)]
    second_times = [base.replace(minute=3), base.replace(minute=1)]

    def to_payload(ts: datetime, name: str) -> dict:
        return {
            "played_at": ts.isoformat().replace("+00:00", "Z"),
            "track": {
                "name": name,
                "artists": [{"name": "Artist"}],
            },
        }

    before_cursor = int(second_times[0].timestamp() * 1000)
    first_page = {
        "items": [
            to_payload(first_times[0], "One"),
            to_payload(first_times[1], "Two"),
        ],
        "next": f"{SpotifyClient.api_root}/me/player/recently-played?before={before_cursor}&limit=2",
    }
    second_page = {
        "items": [
            to_payload(second_times[0], "Three"),
            to_payload(second_times[1], "Four"),
        ],
    }

    after_param = str(int(datetime(2024, 1, 1, 0, 2, tzinfo=timezone.utc).timestamp() * 1000))
    respx_mock.get(
        f"{SpotifyClient.api_root}/me/player/recently-played",
        params={"limit": "2", "after": after_param},
    ).mock(return_value=httpx.Response(200, json=first_page))
    next_route = respx_mock.get(first_page["next"]).mock(
        return_value=httpx.Response(200, json=second_page)
    )

    ingester = SpotifyIngester(page_size=2)
    since = datetime(2024, 1, 1, 0, 2, tzinfo=timezone.utc).timestamp()
    listens = await ingester.fetch_recent("bearer-token", user_id="bob", since=since)

    assert respx_mock.calls.call_count == 2
    assert next_route.calls[0].request.headers["Authorization"] == "Bearer bearer-token"
    listened_at_values = [row["listened_at"] for row in listens]
    assert listened_at_values == [int(ts.timestamp()) for ts in first_times + second_times[:1]]
    assert all(row["user_name"] == "bob" for row in listens)
