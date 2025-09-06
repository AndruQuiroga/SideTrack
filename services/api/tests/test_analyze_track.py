import pytest
from rq import Queue

from sidetrack.api.db import SessionLocal
from sidetrack.api.schemas.tracks import AnalyzeTrackResponse
from sidetrack.common.models import Track


@pytest.mark.asyncio
async def test_analyze_track_schedules_job(async_client, redis_conn):
    async with SessionLocal() as db:
        tr = Track(title="test", path_local="song.mp3")
        db.add(tr)
        await db.commit()
        tid = tr.track_id
    resp = await async_client.post(f"/analyze/track/{tid}")
    assert resp.status_code == 200
    data = AnalyzeTrackResponse.model_validate(resp.json())
    assert data.status == "scheduled"
    q = Queue("analysis", connection=redis_conn)
    jobs = q.jobs
    assert jobs and jobs[0].args[0] == tid


@pytest.mark.asyncio
async def test_analyze_track_not_found(async_client):
    resp = await async_client.post("/analyze/track/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_analyze_track_missing_path(async_client):
    async with SessionLocal() as db:
        tr = Track(title="nop")
        db.add(tr)
        await db.commit()
        tid = tr.track_id
    resp = await async_client.post(f"/analyze/track/{tid}")
    assert resp.status_code == 400
