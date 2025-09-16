from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import Listen, Track
from sidetrack.services.recommendation import InsightEvent, compute_weekly_insights
from sidetrack.worker import jobs as worker_jobs


@pytest.mark.unit
@pytest.mark.asyncio
async def test_compute_weekly_insights_commits_once(async_session, monkeypatch):
    now = datetime.now(UTC)
    t1 = Track(title="t1")
    t2 = Track(title="t2")
    async_session.add_all([t1, t2])
    await async_session.flush()

    listens = [
        Listen(user_id="u1", track_id=t1.track_id, played_at=now - timedelta(days=1)),
        Listen(user_id="u1", track_id=t2.track_id, played_at=now - timedelta(days=2)),
    ]
    async_session.add_all(listens)
    await async_session.commit()

    calls = 0
    orig_commit = AsyncSession.commit

    async def counted_commit(self):
        nonlocal calls
        calls += 1
        await orig_commit(self)

    monkeypatch.setattr(AsyncSession, "commit", counted_commit)

    events = await compute_weekly_insights(async_session, "u1")
    assert calls == 1
    assert {e.type for e in events} == {"weekly_listens", "weekly_unique_tracks"}

    rows = (
        (await async_session.execute(select(InsightEvent).where(InsightEvent.user_id == "u1")))
        .scalars()
        .all()
    )
    assert len(rows) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_compute_weekly_insights_rolls_back(async_session, monkeypatch):
    now = datetime.now(UTC)
    t = Track(title="t1")
    async_session.add(t)
    await async_session.flush()
    async_session.add_all(
        [Listen(user_id="u1", track_id=t.track_id, played_at=now - timedelta(days=1))]
    )
    await async_session.commit()

    async def failing_commit(self):
        raise RuntimeError("boom")

    monkeypatch.setattr(AsyncSession, "commit", failing_commit)

    with pytest.raises(RuntimeError):
        await compute_weekly_insights(async_session, "u1")

    await async_session.rollback()
    rows = (
        (await async_session.execute(select(InsightEvent).where(InsightEvent.user_id == "u1")))
        .scalars()
        .all()
    )
    assert rows == []


def test_generate_weekly_insights_job_creates_events(session):
    now = datetime.now(UTC)
    track = Track(title="job-track")
    session.add(track)
    session.flush()
    session.add(Listen(user_id="u1", track_id=track.track_id, played_at=now - timedelta(days=1)))
    session.commit()

    created = worker_jobs.generate_weekly_insights("u1")
    assert created >= 1

    session.expire_all()
    rows = (
        session.execute(select(InsightEvent).where(InsightEvent.user_id == "u1"))
        .scalars()
        .all()
    )
    assert len(rows) == created
