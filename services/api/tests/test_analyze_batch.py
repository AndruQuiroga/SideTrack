from types import SimpleNamespace

import pytest

from sidetrack.api import main
from sidetrack.api.schemas.tracks import AnalyzeBatchResponse
from sidetrack.api.db import SessionLocal
from sidetrack.common.models import Feature
from tests.factories import TrackFactory

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_analyze_batch_schedules(async_client, monkeypatch):
    async with SessionLocal() as db:
        t1 = TrackFactory(path_local="a.wav")
        t2 = TrackFactory(path_local="b.wav")
        db.add_all([t1, t2])
        await db.flush()
        ids = [t1.track_id, t2.track_id]
        await db.commit()
    dummy = SimpleNamespace(jobs=[])

    class DummyQueue:
        def enqueue(self, func, *args, **kwargs):
            job = SimpleNamespace(args=args, kwargs=kwargs)
            dummy.jobs.append(job)
            return job

    monkeypatch.setattr(main, "Queue", lambda *a, **k: DummyQueue())

    resp = await async_client.post("/analyze/batch", json={"track_ids": ids})
    assert resp.status_code == 200
    data = AnalyzeBatchResponse.model_validate(resp.json())
    assert sorted(data.scheduled) == sorted(ids)
    assert len(dummy.jobs) == 2


@pytest.mark.asyncio
async def test_analyze_batch_skips_existing(async_client, monkeypatch):
    async with SessionLocal() as db:
        t1 = TrackFactory(path_local="a.wav")
        t2 = TrackFactory(path_local="b.wav")
        db.add_all([t1, t2])
        await db.flush()
        await db.commit()
        db.add(Feature(track_id=t1.track_id))
        await db.commit()
        ids = [t1.track_id, t2.track_id]
    dummy = SimpleNamespace(jobs=[])

    class DummyQueue:
        def enqueue(self, func, *args, **kwargs):
            job = SimpleNamespace(args=args, kwargs=kwargs)
            dummy.jobs.append(job)
            return job

    monkeypatch.setattr(main, "Queue", lambda *a, **k: DummyQueue())

    resp = await async_client.post("/analyze/batch", json={"track_ids": ids})
    assert resp.status_code == 200
    data = AnalyzeBatchResponse.model_validate(resp.json())
    assert data.already == [t1.track_id]
    assert data.scheduled == [t2.track_id]
    assert len(dummy.jobs) == 1
