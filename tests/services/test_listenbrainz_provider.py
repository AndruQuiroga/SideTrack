import httpx
import pytest

from sidetrack.services.providers.listenbrainz import ListenBrainzIngester


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_recent_paginates_and_normalises(respx_mock):
    page_one = [
        {
            "listened_at": 300,
            "track_metadata": {
                "artist_name": "Artist A",
                "track_name": "Track A",
                "additional_info": {"recording_mbid": "rec-1"},
            },
        },
        {
            "listened_at": 200,
            "track_metadata": {
                "artist_name": "Artist B",
                "title": "Track B",
            },
        },
    ]
    page_two = [
        {
            "listened_at": 150,
            "track_metadata": {
                "artist": "Artist C",
                "track_name": "Track C",
                "mbid_mapping": {"recording_mbid": "rec-3"},
            },
        }
    ]

    route = respx_mock.get("https://api.listenbrainz.org/1/user/tester/listens")
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "payload": {
                    "listens": page_one,
                    "next": {"next": "cursor-1", "payload": "token-1"},
                }
            },
        ),
        httpx.Response(200, json={"payload": {"listens": page_two}}),
    ]

    ingester = ListenBrainzIngester(page_size=2)
    listens = await ingester.fetch_recent("tester", since=99)

    assert [row["listened_at"] for row in listens] == [300, 200, 150]
    assert listens[0]["track_metadata"]["mbid_mapping"]["recording_mbid"] == "rec-1"
    assert listens[1]["track_metadata"]["track_name"] == "Track B"
    assert listens[2]["track_metadata"]["artist_name"] == "Artist C"
    assert all(row["user_name"] == "tester" for row in listens)

    assert route.call_count == 2
    first_query = dict(route.calls[0].request.url.params)
    second_query = dict(route.calls[1].request.url.params)
    assert first_query["count"] == "2"
    assert "next" not in first_query
    assert first_query["min_ts"] == "100"
    assert second_query["next"] == "cursor-1"
    assert second_query["payload"] == "token-1"
    assert second_query["count"] == "2"
    assert second_query["min_ts"] == "100"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_recent_includes_auth_token(respx_mock):
    payload = {
        "listened_at": 170,
        "track_metadata": {
            "artist_name": "Artist",
            "track_name": "Title",
        },
    }

    route = respx_mock.get("https://api.listenbrainz.org/1/user/alice/listens").mock(
        return_value=httpx.Response(200, json={"payload": {"listens": [payload]}})
    )

    ingester = ListenBrainzIngester()
    listens = await ingester.fetch_recent("alice", token="secret-token")

    assert listens[0]["listened_at"] == 170
    assert route.called
    assert route.calls[0].request.headers["Authorization"] == "Token secret-token"
