import pytest

from sidetrack.api.db import SessionLocal
from tests.factories import EmbeddingFactory, FeatureFactory, TrackFactory

pytestmark = pytest.mark.integration


async def _create_track_with_features() -> int:
    async with SessionLocal() as db:
        tr = TrackFactory()
        db.add(tr)
        await db.flush()
        tid = tr.track_id
        db.add(
            FeatureFactory(
                track_id=tid,
                bpm=120.0,
                pumpiness=0.5,
                percussive_harmonic_ratio=0.3,
            )
        )
        db.add(
            EmbeddingFactory(
                track_id=tid,
                model="m",
                dim=3,
                vector=[0.1, 0.2, 0.3],
            )
        )
        await db.commit()
        return tid


@pytest.mark.asyncio
async def test_get_track_features_returns_rows(async_client):
    tid = await _create_track_with_features()
    resp = await async_client.get(f"/tracks/{tid}/features")
    assert resp.status_code == 200
    data = resp.json()
    assert data["feature"]["bpm"] == 120.0
    assert data["embedding"]["model"] == "m"


@pytest.mark.asyncio
async def test_get_track_features_not_found(async_client):
    resp = await async_client.get("/tracks/9999/features")
    assert resp.status_code == 404
