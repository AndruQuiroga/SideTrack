import pytest
from fastapi import HTTPException
from sqlalchemy import select

from sidetrack.api.constants import AXES
from sidetrack.api.main import score_track
from sidetrack.common.models import Embedding, Feature, MoodScore, Track


@pytest.mark.asyncio
async def test_score_track_zero_shot(async_session):
    tr = Track(title="Song")
    async_session.add(tr)
    await async_session.flush()
    async_session.add(
        Embedding(track_id=tr.track_id, model="test", dim=3, vector=[0.1, 0.2, 0.3])
    )
    await async_session.commit()

    res = await score_track(tr.track_id, db=async_session)
    assert res["detail"] == "scored"
    assert set(res["scores"]) == set(AXES)

    rows = (
        await async_session.execute(
            select(MoodScore).where(MoodScore.track_id == tr.track_id)
        )
    ).scalars().all()
    assert len(rows) == len(AXES)
    for row in rows:
        assert 0.0 <= row.value <= 1.0
        assert row.method == "zero"
    for val in res["scores"].values():
        assert 0.0 <= val["value"] <= 1.0
        assert 0.0 <= val["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_score_track_logreg(async_session):
    tr = Track(title="Song2")
    async_session.add(tr)
    await async_session.flush()
    async_session.add(
        Feature(
            track_id=tr.track_id,
            bpm=120.0,
            pumpiness=0.5,
            percussive_harmonic_ratio=0.4,
        )
    )
    await async_session.commit()

    res = await score_track(tr.track_id, method="logreg", version="v1", db=async_session)
    assert res["detail"] == "scored"
    assert res["method"] == "logreg_v1"
    assert set(res["scores"]) == set(AXES)
    rows = (
        await async_session.execute(
            select(MoodScore).where(
                MoodScore.track_id == tr.track_id, MoodScore.method == "logreg_v1"
            )
        )
    ).scalars().all()
    assert len(rows) == len(AXES)
    for val in res["scores"].values():
        assert 0.0 <= val["value"] <= 1.0
        assert 0.0 <= val["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_score_track_missing_data(async_session):
    tr = Track(title="NoData")
    async_session.add(tr)
    await async_session.commit()

    with pytest.raises(HTTPException):
        await score_track(tr.track_id, db=async_session)


@pytest.mark.asyncio
async def test_score_track_bad_method(async_session):
    tr = Track(title="Bad")
    async_session.add(tr)
    await async_session.commit()
    with pytest.raises(HTTPException):
        await score_track(tr.track_id, method="nope", db=async_session)
