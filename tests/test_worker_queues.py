"""Exercise the library's real queue claims and locks on Postgres."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from time import monotonic

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from sidetrack import db as database
from sidetrack.queue_client import enqueue
from sidetrack.request_pacing import wait_for_musicbrainz
from sidetrack.worker import create_worker_app, selected_queues


def test_queue_selection():
    assert selected_queues("default,musicbrainz") == ["default", "musicbrainz"]
    assert selected_queues("gpu") == ["gpu"]
    with pytest.raises(ValueError):
        selected_queues("default,gpu")
    with pytest.raises(ValueError):
        selected_queues("unknown")


@pytest.mark.parametrize("concurrency", [1, 2])
def test_two_cpu_workers_isolate_and_serialize(engine, database_url, concurrency):
    with Session(engine) as db:
        for queue in ["default", "default", "musicbrainz", "musicbrainz", "gpu"]:
            enqueue(db, "test-record", {"queue": queue}, queue=queue)
        db.commit()
    active = {"default": 0, "musicbrainz": 0}
    peaks = active.copy()
    seen = []

    async def work():
        default_overlap = asyncio.Event()
        musicbrainz_started = asyncio.Event()
        release_musicbrainz = asyncio.Event()
        probe_completed = asyncio.Event()
        all_completed = asyncio.Event()
        completed = 0

        async def record(job_id, task, arguments):
            nonlocal completed
            queue = arguments["queue"]
            if queue == "probe":
                probe_completed.set()
                return
            seen.append(queue)
            active[queue] += 1
            peaks[queue] = max(peaks[queue], active[queue])
            if queue == "default":
                if active[queue] == 2:
                    default_overlap.set()
                await default_overlap.wait()
            else:
                musicbrainz_started.set()
                await release_musicbrainz.wait()
            active[queue] -= 1
            completed += 1
            if completed == 4:
                all_completed.set()

        async def one():
            app = create_worker_app(database_url)
            app.tasks["sidetrack.execute"].func = record
            async with app.open_async():
                await app.run_worker_async(
                    queues=["default", "musicbrainz"],
                    concurrency=concurrency,
                    wait=True,
                    fetch_job_polling_interval=0.01,
                    install_signal_handlers=False,
                    listen_notify=False,
                )

        workers = [asyncio.create_task(one()), asyncio.create_task(one())]
        try:
            await asyncio.wait_for(default_overlap.wait(), timeout=10)
            await asyncio.wait_for(musicbrainz_started.wait(), timeout=10)
            # Keep the first serialized job running while another runnable job
            # proves the workers continue polling around the locked second job.
            with Session(engine) as db:
                enqueue(db, "test-record", {"queue": "probe"})
                db.commit()
            await asyncio.wait_for(probe_completed.wait(), timeout=10)
            with engine.connect() as conn:
                states = conn.scalars(
                    text(
                        "SELECT status::text FROM job_queue.procrastinate_jobs "
                        "WHERE queue_name='musicbrainz'"
                    )
                ).all()
            assert sorted(states) == ["doing", "todo"]
            release_musicbrainz.set()
            await asyncio.wait_for(all_completed.wait(), timeout=10)
        finally:
            default_overlap.set()
            release_musicbrainz.set()
            for worker in workers:
                worker.cancel()
            results = await asyncio.gather(*workers, return_exceptions=True)
            assert all(isinstance(result, asyncio.CancelledError) for result in results), results

    try:
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(work())
        assert seen.count("default") == 2
        assert seen.count("musicbrainz") == 2
        assert peaks["musicbrainz"] == 1
        assert peaks["default"] == 2
        with engine.connect() as conn:
            assert (
                conn.scalar(
                    text(
                        "SELECT status::text FROM job_queue.procrastinate_jobs "
                        "WHERE queue_name='gpu'"
                    )
                )
                == "todo"
            )
    finally:
        with engine.begin() as conn:
            conn.execute(text("SET LOCAL search_path TO job_queue,public"))
            conn.execute(text("DELETE FROM procrastinate_jobs"))
            conn.execute(text("DELETE FROM background_jobs"))


def test_request_pacing_across_connections(engine, monkeypatch):
    monkeypatch.setattr(database, "_engine", engine)

    def request_start():
        wait_for_musicbrainz()
        return monotonic()

    with ThreadPoolExecutor(max_workers=2) as pool:
        starts = sorted(pool.map(lambda _: request_start(), range(2)))
    assert starts[1] - starts[0] >= 1


def test_unimplemented_task_reports_unavailable(engine, monkeypatch):
    from sidetrack.job_runner import run

    monkeypatch.setattr(database, "_engine", engine)
    with Session(engine) as db:
        row = enqueue(db, "analysis.unimplemented_gpu", {}, queue="gpu")
        job_id, queue_id = row.id, row.queue_job_id
        db.commit()
    try:
        assert run(job_id) == 2
        with Session(engine) as db:
            assert db.get(type(row), job_id).result is None
    finally:
        with engine.begin() as conn:
            conn.execute(text("SET LOCAL search_path TO job_queue,public"))
            conn.execute(text("DELETE FROM procrastinate_jobs WHERE id=:id"), {"id": queue_id})
            conn.execute(text("DELETE FROM background_jobs WHERE id=:id"), {"id": job_id})
