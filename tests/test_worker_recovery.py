"""Kill real workers at a database barrier, then recover accepted work."""

import os
import signal
import subprocess
import sys
import time
from contextlib import contextmanager

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from sidetrack.analysis import TasteProfile
from sidetrack.identity import User
from sidetrack.queue_client import enqueue
from sidetrack.queue_maintenance import recover_stalled
from sidetrack.queue_models import BackgroundJob


def start_worker(database_url):
    return subprocess.Popen(
        [sys.executable, "-m", "sidetrack.worker", "--once"],
        env={**os.environ, "DATABASE_URL": database_url},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=sys.platform != "win32",
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def kill_tree(process):
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=True
        )
    else:
        os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=10)


def await_status(engine, job_id, wanted, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with Session(engine) as db:
            row = db.get(BackgroundJob, job_id)
            if row.status == wanted:
                return row.attempts
        time.sleep(0.05)
    raise AssertionError(f"Job never reached {wanted}")


@contextmanager
def accepted_job(engine):
    with Session(engine) as db:
        user = User(display_name="Recovery fixture")
        db.add(user)
        db.flush()
        row = enqueue(db, "analysis.recompute_taste_profile", {"user_id": str(user.id)})
        job_id, user_id, queue_id = row.id, user.id, row.queue_job_id
        db.commit()
    try:
        yield job_id, user_id
    finally:
        with engine.begin() as conn:
            conn.execute(text("SET LOCAL search_path TO job_queue,public"))
            conn.execute(text("DELETE FROM procrastinate_jobs WHERE id=:id"), {"id": queue_id})
            conn.execute(delete(BackgroundJob).where(BackgroundJob.id == job_id))
            conn.execute(delete(User).where(User.id == user_id))


def test_real_worker_runs_and_replay_keeps_one_profile(engine, database_url):
    with accepted_job(engine) as (job_id, user_id):
        process = start_worker(database_url)
        try:
            assert process.wait(timeout=20) == 0
            assert await_status(engine, job_id, "finished") == 1
            with Session(engine) as db:
                assert (
                    len(
                        db.scalars(
                            select(TasteProfile).where(TasteProfile.user_id == user_id)
                        ).all()
                    )
                    == 1
                )
                assert db.get(BackgroundJob, job_id).result["user_id"] == str(user_id)
                # Simulate a lost acknowledgment after the atomic result commit.
                db.execute(text("SET LOCAL search_path TO job_queue,public"))
                db.execute(
                    text(
                        "UPDATE procrastinate_jobs SET status='doing', worker_id=NULL "
                        "WHERE id=:id"
                    ),
                    {"id": db.get(BackgroundJob, job_id).queue_job_id},
                )
                assert recover_stalled(db, seconds=0) == 1
                db.commit()
            replay = start_worker(database_url)
            try:
                assert replay.wait(timeout=20) == 0
                assert await_status(engine, job_id, "finished") == 1
            finally:
                kill_tree(replay)
        finally:
            kill_tree(process)


def test_crash_before_commit_recovers_and_attempts_are_bounded(engine, database_url):
    with accepted_job(engine) as (job_id, user_id):
        for attempt in range(1, 4):
            # Domain execution blocks here while queue acceptance/attempt writes remain visible.
            with engine.connect() as barrier:
                transaction = barrier.begin()
                barrier.execute(text("LOCK TABLE taste_profiles IN ACCESS EXCLUSIVE MODE"))
                process = start_worker(database_url)
                try:
                    assert await_status(engine, job_id, "started") == attempt
                    kill_tree(process)
                finally:
                    kill_tree(process)
                    transaction.rollback()
            with Session(engine) as db:
                assert recover_stalled(db, seconds=0) == 1
                db.commit()
        assert await_status(engine, job_id, "failed") == 3
        with Session(engine) as db:
            assert not db.scalars(select(TasteProfile).where(TasteProfile.user_id == user_id)).all()


@pytest.mark.skipif(
    sys.platform == "win32", reason="SIGTERM semantics are verified in the Linux image"
)
def test_sigterm_finishes_claimed_work_before_shutdown(engine, database_url):
    with accepted_job(engine) as (job_id, user_id):
        with engine.connect() as barrier:
            transaction = barrier.begin()
            barrier.execute(text("LOCK TABLE taste_profiles IN ACCESS EXCLUSIVE MODE"))
            process = start_worker(database_url)
            try:
                await_status(engine, job_id, "started")
                process.send_signal(signal.SIGTERM)
                transaction.rollback()
                assert process.wait(timeout=15) == 0
                assert await_status(engine, job_id, "finished") == 1
            finally:
                if transaction.is_active:
                    transaction.rollback()
                kill_tree(process)


@pytest.mark.parametrize("interrupt", ["timeout", "cancel", "launch"])
def test_executor_terminates_child_and_preserves_retry(engine, monkeypatch, interrupt):
    import asyncio

    from sidetrack import db as database
    from sidetrack import worker

    monkeypatch.setattr(database, "_engine", engine)
    real_popen = subprocess.Popen
    spawned = []

    def hanging_runner(*args, **kwargs):
        if interrupt == "launch":
            raise OSError("private-marker")
        process = real_popen([sys.executable, "-c", "import time; time.sleep(60)"], **kwargs)
        spawned.append(process)
        return process

    monkeypatch.setattr(worker.subprocess, "Popen", hanging_runner)
    original_wait = asyncio.wait_for

    async def short_wait(future, *, timeout):
        return await original_wait(future, timeout=0.1)

    if interrupt == "timeout":
        monkeypatch.setattr(worker.asyncio, "wait_for", short_wait)
    with accepted_job(engine) as (job_id, user_id):

        async def execute():
            task = asyncio.create_task(
                worker.execute(str(job_id), "analysis.recompute_taste_profile", {})
            )
            if interrupt == "cancel":
                while not spawned:
                    await asyncio.sleep(0.01)
                task.cancel()
            with pytest.raises(worker.ExecutionFailed):
                await task

        try:
            asyncio.run(execute())
            assert not spawned if interrupt == "launch" else spawned[0].poll() is not None
            with Session(engine) as db:
                row = db.get(BackgroundJob, job_id)
                assert row.status == "deferred" and row.attempts == 1
                assert row.error == "execution_failed"
        finally:
            for process in spawned:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
