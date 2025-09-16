from types import SimpleNamespace

import pytest

from sidetrack.api import main
from sidetrack.db import async_session_scope
from sidetrack.api.schemas.tracks import AnalyzeTrackResponse
from tests.factories import TrackFactory

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_analyze_track_schedules_job(async_client, monkeypatch):
    async with async_session_scope() as db:
        tr = TrackFactory(path_local="song.mp3")
        db.add(tr)
        await db.flush()
        tid = tr.track_id
        await db.commit()
    dummy = SimpleNamespace(jobs=[])

    class DummyQueue:
        def enqueue(self, func, *args, **kwargs):
            job = SimpleNamespace(args=args, kwargs=kwargs)
            dummy.jobs.append(job)
            return job

    monkeypatch.setattr(main, "Queue", lambda *a, **k: DummyQueue())

    resp = await async_client.post(f"/analyze/track/{tid}")
    assert resp.status_code == 200
    data = AnalyzeTrackResponse.model_validate(resp.json())
    assert data.status == "scheduled"
    assert dummy.jobs and dummy.jobs[0].args[0] == tid


@pytest.mark.asyncio
async def test_analyze_track_not_found(async_client):
    resp = await async_client.post("/analyze/track/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_analyze_track_missing_path(async_client):
    async with async_session_scope() as db:
        tr = TrackFactory()
        db.add(tr)
        await db.flush()
        tid = tr.track_id
        await db.commit()
    resp = await async_client.post(f"/analyze/track/{tid}")
    assert resp.status_code == 400
