import logging
from datetime import UTC, date, datetime

import httpx
import pytest

from sidetrack.services.listenbrainz import ListenBrainzClient
from sidetrack.services.recommendation import _listenbrainz_candidates


class _ConcreteListenBrainzClient(ListenBrainzClient):
    def auth_url(self, callback: str) -> str:  # pragma: no cover - not used in tests
        raise NotImplementedError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_listenbrainz_candidates_normalization(snapshot):
    class StubLB:
        async def get_cf_recommendations(self, user: str, limit: int = 50):
            return [
                {
                    "recording_mbid": "rec1",
                    "recording_name": "Track A",
                    "artist_name": "Artist A",
                    "score": 0.9,
                },
                {
                    "recording_mbid": "rec2",
                    "recording_name": "Track B",
                    "artist_name": "Artist B",
                    "score": 0.8,
                },
            ]

    result = await _listenbrainz_candidates(StubLB(), "alice")
    snapshot.assert_match([c.to_dict() for c in result])


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["recommendations", "recordings", "recommended_recordings"])
async def test_get_cf_recommendations_contract(snapshot, respx_mock, key):
    payload = {
        key: [
            {
                "recording_mbid": "rec1",
                "recording_name": "Track A",
                "artist_name": "Artist A",
                "score": 0.9,
            },
            {
                "recording_mbid": "rec2",
                "recording_name": "Track B",
                "artist_name": "Artist B",
                "score": 0.8,
            },
        ]
    }

    respx_mock.get(
        "https://api.listenbrainz.org/1/user/alice/cf/recommendations"
    ).respond(200, json=payload)

    async with httpx.AsyncClient() as client:
        service = _ConcreteListenBrainzClient(client)
        result = await service.get_cf_recommendations("alice")

    snapshot.assert_match(result)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_cf_recommendations_unexpected_payload(respx_mock, caplog):
    respx_mock.get(
        "https://api.listenbrainz.org/1/user/alice/cf/recommendations"
    ).respond(200, json={"foo": []})

    caplog.set_level(logging.WARNING)
    async with httpx.AsyncClient() as client:
        service = _ConcreteListenBrainzClient(client)
        with pytest.raises(RuntimeError):
            await service.get_cf_recommendations("alice")

    assert "unexpected ListenBrainz recommendations payload" in caplog.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_listens_paginates_until_limit(respx_mock):
    page_one = [
        {"listened_at": 400},
        {"listened_at": 350},
    ]
    page_two = [
        {"listened_at": 300},
        {"listened_at": 250},
    ]

    route = respx_mock.get("https://api.listenbrainz.org/1/user/alice/listens")
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "payload": {
                    "listens": page_one,
                    "next": {"next": "cursor-1", "payload": "payload-1"},
                }
            },
        ),
        httpx.Response(
            200,
            json={
                "payload": {"listens": page_two},
                "links": {
                    "next": "/1/user/alice/listens?next=cursor-2&payload=payload-2"
                },
            },
        ),
    ]

    since = date(2023, 1, 1)
    async with httpx.AsyncClient() as client:
        service = _ConcreteListenBrainzClient(client)
        listens = await service.fetch_listens("alice", since, token="secret", limit=3)

    assert listens == page_one + page_two[:1]
    assert route.call_count == 2

    min_ts = int(datetime.combine(since, datetime.min.time(), tzinfo=UTC).timestamp())
    first_query = dict(route.calls[0].request.url.params)
    second_query = dict(route.calls[1].request.url.params)

    assert first_query["count"] == "3"
    assert first_query["min_ts"] == str(min_ts)
    assert second_query["next"] == "cursor-1"
    assert second_query["payload"] == "payload-1"
    assert second_query["count"] == "1"
    assert second_query["min_ts"] == str(min_ts)
    assert route.calls[0].request.headers["Authorization"] == "Token secret"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_listens_follows_string_cursor(respx_mock):
    route = respx_mock.get("https://api.listenbrainz.org/1/user/bob/listens")
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "payload": {"listens": [{"idx": 1}]},
                "links": {"next": "/1/user/bob/listens?next=abc&payload=def"},
            },
        ),
        httpx.Response(
            200,
            json={
                "listens": [{"idx": 2}],
                "next": "?next=ghi&payload=jkl",
            },
        ),
        httpx.Response(200, json={"payload": {"listens": [{"idx": 3}]}}),
    ]

    async with httpx.AsyncClient() as client:
        service = _ConcreteListenBrainzClient(client)
        listens = await service.fetch_listens("bob", None, limit=5)

    assert listens == [{"idx": 1}, {"idx": 2}, {"idx": 3}]
    assert route.call_count == 3

    first_query = dict(route.calls[0].request.url.params)
    second_query = dict(route.calls[1].request.url.params)
    third_query = dict(route.calls[2].request.url.params)

    assert first_query["count"] == "5"
    assert second_query["next"] == "abc"
    assert second_query["payload"] == "def"
    assert second_query["count"] == "4"
    assert third_query["next"] == "ghi"
    assert third_query["payload"] == "jkl"
    assert third_query["count"] == "3"
