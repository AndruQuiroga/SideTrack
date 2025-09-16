import pytest

from sidetrack.services.recommendation import profile_from_spotify


class _FakeSpotify:
    def __init__(self, recent: list[dict], features: list[dict]):
        self._recent = recent
        self._features = features
        self.requested_ids: list[str] | None = None

    async def get_recently_played(self) -> list[dict]:
        return self._recent

    async def get_audio_features_batch(self, ids: list[str]) -> list[dict]:
        self.requested_ids = ids
        return self._features


@pytest.mark.unit
@pytest.mark.asyncio
async def test_profile_from_spotify_uses_batch_and_normalises() -> None:
    service = _FakeSpotify(
        recent=[
            {"track": {"id": "a1"}},
            {"track": {"id": "a2"}},
            {"track": {"id": None}},
        ],
        features=[
            {"tempo": 130.0, "valence": 1.2, "energy": 0.9},
            {"tempo": 110.0, "valence": -0.4, "energy": 1.5},
        ],
    )

    profile = await profile_from_spotify(service)  # type: ignore[arg-type]

    assert service.requested_ids == ["a1", "a2"]
    assert profile == pytest.approx({"tempo": 120.0, "valence": 0.4, "energy": 1.0})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_profile_from_spotify_handles_empty_recent() -> None:
    class _EmptySpotify(_FakeSpotify):
        async def get_audio_features_batch(self, ids: list[str]) -> list[dict]:  # pragma: no cover - should not be called
            raise AssertionError("get_audio_features_batch should not be called")

    service = _EmptySpotify(recent=[{"track": {}}, {}], features=[])

    profile = await profile_from_spotify(service)  # type: ignore[arg-type]

    assert profile == {"tempo": 0.0, "valence": 0.0, "energy": 0.0}
