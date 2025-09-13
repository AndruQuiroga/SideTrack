import httpx
import pytest

from sidetrack.services.listenbrainz import ListenBrainzClient
from sidetrack.services.candidates import _listenbrainz_candidates


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
    snapshot.assert_match(result)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_cf_recommendations_contract(snapshot, respx_mock):
    payload = {
        "recommendations": [
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
        service = ListenBrainzClient(client)
        result = await service.get_cf_recommendations("alice")

    snapshot.assert_match(result)
