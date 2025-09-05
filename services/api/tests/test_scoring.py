import os
import sys

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from services.api.app.constants import AXES
from services.api.app.main import score_track
from services.common.models import Base, Embedding, Feature, MoodScore, Track


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    with SessionLocal() as sess:
        yield sess


def test_score_track_zero_shot(session):
    tr = Track(title="Song")
    session.add(tr)
    session.flush()
    session.add(Embedding(track_id=tr.track_id, model="test", dim=3, vector=[0.1, 0.2, 0.3]))
    session.commit()

    res = score_track(tr.track_id, db=session)
    assert res["detail"] == "scored"
    assert set(res["scores"]) == set(AXES)

    rows = (
        session.execute(select(MoodScore).where(MoodScore.track_id == tr.track_id)).scalars().all()
    )
    assert len(rows) == len(AXES)
    for row in rows:
        assert 0.0 <= row.value <= 1.0
        assert row.method == "zero"
    for val in res["scores"].values():
        assert 0.0 <= val["value"] <= 1.0
        assert 0.0 <= val["confidence"] <= 1.0


def test_score_track_logreg(session):
    tr = Track(title="Song2")
    session.add(tr)
    session.flush()
    session.add(
        Feature(
            track_id=tr.track_id,
            bpm=120.0,
            pumpiness=0.5,
            percussive_harmonic_ratio=0.4,
        )
    )
    session.commit()

    res = score_track(tr.track_id, method="logreg", version="v1", db=session)
    assert res["detail"] == "scored"
    assert res["method"] == "logreg_v1"
    assert set(res["scores"]) == set(AXES)
    rows = (
        session.execute(
            select(MoodScore).where(
                MoodScore.track_id == tr.track_id, MoodScore.method == "logreg_v1"
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == len(AXES)
    for val in res["scores"].values():
        assert 0.0 <= val["value"] <= 1.0
        assert 0.0 <= val["confidence"] <= 1.0


def test_score_track_missing_data(session):
    tr = Track(title="NoData")
    session.add(tr)
    session.commit()

    with pytest.raises(HTTPException):
        score_track(tr.track_id, db=session)


def test_score_track_bad_method(session):
    tr = Track(title="Bad")
    session.add(tr)
    session.commit()
    with pytest.raises(HTTPException):
        score_track(tr.track_id, method="nope", db=session)
