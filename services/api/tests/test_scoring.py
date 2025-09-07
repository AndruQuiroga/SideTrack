import pytest
from fastapi import HTTPException
from sqlalchemy import select

from sidetrack.api.constants import AXES
from sidetrack.api.main import score_track
from sidetrack.common.models import MoodScore
from tests.factories import EmbeddingFactory, FeatureFactory, TrackFactory

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_score_track_zero_shot(async_session):
    tr = TrackFactory()
    async_session.add(tr)
    await async_session.flush()
    tid = tr.track_id
    async_session.add(EmbeddingFactory(unit=True, track_id=tid))
    await async_session.commit()

    res = await score_track(tid, db=async_session)
    assert res["detail"] == "scored"
    assert set(res["scores"]) == set(AXES)

    rows = (
        (await async_session.execute(select(MoodScore).where(MoodScore.track_id == tid)))
        .scalars()
        .all()
    )
    assert len(rows) == len(AXES)
    for row in rows:
        assert 0.0 <= row.value <= 1.0
        assert row.method == "zero"
    for val in res["scores"].values():
        assert 0.0 <= val["value"] <= 1.0
        assert 0.0 <= val["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_score_track_logreg(async_session):
    tr = TrackFactory()
    async_session.add(tr)
    await async_session.flush()
    tid = tr.track_id
    async_session.add(
        FeatureFactory(
            track_id=tid,
            bpm=120.0,
            pumpiness=0.5,
            percussive_harmonic_ratio=0.4,
        )
    )
    await async_session.commit()

    res = await score_track(tid, method="logreg", version="v1", db=async_session)
    assert res["detail"] == "scored"
    assert res["method"] == "logreg_v1"
    assert set(res["scores"]) == set(AXES)
    rows = (
        (
            await async_session.execute(
                select(MoodScore).where(MoodScore.track_id == tid, MoodScore.method == "logreg_v1")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == len(AXES)
    for val in res["scores"].values():
        assert 0.0 <= val["value"] <= 1.0
        assert 0.0 <= val["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_score_track_missing_data(async_session):
    tr = TrackFactory()
    async_session.add(tr)
    await async_session.flush()
    tid = tr.track_id
    await async_session.commit()

    with pytest.raises(HTTPException):
        await score_track(tid, db=async_session)


@pytest.mark.asyncio
async def test_score_track_bad_method(async_session):
    tr = TrackFactory()
    async_session.add(tr)
    await async_session.flush()
    tid = tr.track_id
    await async_session.commit()
    with pytest.raises(HTTPException):
        await score_track(tid, method="nope", db=async_session)
