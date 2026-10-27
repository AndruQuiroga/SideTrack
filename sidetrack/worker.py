"""Postgres queue worker. Migrations must run before this process starts."""

from __future__ import annotations

import argparse
import asyncio
import logging
import subprocess
import sys
from uuid import UUID

import procrastinate
from procrastinate import signals
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from sidetrack.analysis.embeddings import TASK as EMBED_AUDIO
from sidetrack.analysis.embeddings import TIME_LIMIT_S as EMBED_AUDIO_LIMIT_S
from sidetrack.config import get_settings
from sidetrack.db import database_now, get_engine, init_engine
from sidetrack.queue_maintenance import reconcile_schedules, recover_stalled, seed_cleanup
from sidetrack.queue_models import BackgroundJob

# Seconds a job's child process may run, by task; everything else gets 300.
TIME_LIMITS = {"listening.ingest_lastfm": 600, EMBED_AUDIO: EMBED_AUDIO_LIMIT_S}


class ExecutionFailed(Exception):
    """Safe error for transient domain execution failures."""


class Unavailable(Exception):
    """Safe permanent error for unsupported or invalid work."""


def selected_queues(value: str) -> list[str]:
    queues = value.split(",")
    if not queues or any(q not in {"default", "musicbrainz", "gpu"} for q in queues):
        raise ValueError("Queues must be default,musicbrainz or gpu")
    if "gpu" in queues and queues != ["gpu"]:
        raise ValueError("GPU queue requires a dedicated worker")
    return queues


async def execute(job_id: str, task: str, arguments: dict) -> None:
    uid = UUID(job_id)
    with Session(get_engine()) as db, db.begin():
        row = db.get(BackgroundJob, uid, with_for_update=True)
        if row is None:
            raise Unavailable("job_unavailable")
        if row.status == "finished":
            return
        if row.attempts >= 3:
            row.status, row.error = "failed", "attempts_exhausted"
            row.finished_at = database_now(db)
            exhausted = True
        else:
            exhausted = False
            row.attempts += 1
            row.status, row.error = "started", None
    if exhausted:
        raise Unavailable("attempts_exhausted")
    timeout = TIME_LIMITS.get(task, 300)
    process = None
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "sidetrack.job_runner", job_id, str(timeout)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        code = await asyncio.wait_for(asyncio.to_thread(process.wait), timeout=timeout)
    except BaseException as exc:
        if process is not None and process.poll() is None:
            process.kill()
            await asyncio.to_thread(process.wait)
        if isinstance(exc, OSError | asyncio.TimeoutError | asyncio.CancelledError):
            code = 1
        else:
            raise
    if code == 0:
        return
    with Session(get_engine()) as db, db.begin():
        row = db.get(BackgroundJob, uid, with_for_update=True)
        if row is None:
            raise Unavailable("job_unavailable")
        permanent = code == 2 or row.attempts >= 3
        row.status = "failed" if permanent else "deferred"
        row.error = "unavailable" if code == 2 else "execution_failed"
        if permanent:
            row.finished_at = database_now(db)
    if code == 2:
        raise Unavailable("unavailable")
    raise ExecutionFailed("execution_failed")


def create_worker_app(database_url: str) -> procrastinate.App:
    url = make_url(database_url).set(drivername="postgresql")
    connector = procrastinate.PsycopgConnector(
        conninfo=url.render_as_string(hide_password=False),
        kwargs={"options": "-c search_path=job_queue,public", "connect_timeout": 5},
        min_size=1,
        max_size=5,
    )
    app = procrastinate.App(connector=connector)
    app.task(
        name="sidetrack.execute",
        retry=procrastinate.RetryStrategy(
            max_attempts=2, exponential_wait=2, retry_exceptions=(ExecutionFailed, SQLAlchemyError)
        ),
    )(execute)
    return app


def maintenance_tick():
    with Session(get_engine()) as db, db.begin():
        recover_stalled(db)
        seed_cleanup(db)
        reconcile_schedules(db)


async def run_worker(app, *, queues, once=False):
    async def maintain():
        while True:
            try:
                await asyncio.to_thread(maintenance_tick)
            except SQLAlchemyError:
                logging.getLogger(__name__).warning("Queue maintenance unavailable; retrying")
            await asyncio.sleep(1)

    async with app.open_async():
        await asyncio.to_thread(maintenance_tick)
        maintenance = asyncio.create_task(maintain())
        worker = asyncio.create_task(
            app.run_worker_async(
                queues=queues,
                concurrency=1 if queues == ["gpu"] else 4,  # one model on the GPU
                shutdown_graceful_timeout=30,
                wait=not once,
                fetch_job_polling_interval=1,
                install_signal_handlers=False,
            )
        )
        stop_requested = False

        def stop():
            nonlocal stop_requested
            stop_requested = True
            # Procrastinate shields execution and drains its current jobs when
            # its run task is canceled, honoring shutdown_graceful_timeout.
            worker.cancel()

        try:
            # The library's --once signal scope ends before its drain wait.
            # Own the scope here so SIGTERM stays graceful for the whole run.
            with signals.on_stop(stop):
                done, _ = await asyncio.wait(
                    {worker, maintenance}, return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    if task is worker and task.cancelled() and stop_requested:
                        continue
                    task.result()
        finally:
            maintenance.cancel()
            worker.cancel()
            await asyncio.gather(maintenance, worker, return_exceptions=True)


def main():
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queues", default="default,musicbrainz")
    parser.add_argument(
        "--once", action="store_true", help="Drain currently runnable jobs and exit"
    )
    args = parser.parse_args()
    queues = selected_queues(args.queues)
    settings = get_settings()
    init_engine(settings.database_url)
    asyncio.run(run_worker(create_worker_app(settings.database_url), queues=queues, once=args.once))


if __name__ == "__main__":
    main()
