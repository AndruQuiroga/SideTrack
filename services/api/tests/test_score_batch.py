import pytest
from sqlalchemy import select

from sidetrack.api.main import score_batch
from sidetrack.api.schemas.scoring import ScoreBatchIn
from sidetrack.common.models import TrackScore
from tests.factories import EmbeddingFactory, FeatureFactory, TrackFactory

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_score_batch(async_session):
    tr = TrackFactory()
    async_session.add(tr)
    await async_session.flush()
    tid = tr.track_id
    async_session.add(FeatureFactory(track_id=tid))
    async_session.add(EmbeddingFactory(track_id=tid))
    await async_session.commit()

    payload = ScoreBatchIn(track_ids=[tid], model="test")
    res = await score_batch(payload, db=async_session)
    assert res["detail"] == "scored"
    assert res["upserts"] == 4

    rows = (
        await async_session.execute(select(TrackScore).where(TrackScore.track_id == tid))
    ).scalars()
    data = {row.metric: row.value for row in rows}
    assert data == {
        "energy": 0.5,
        "danceability": 0.6,
        "valence": 0.1,
        "acousticness": 0.2,
    }
