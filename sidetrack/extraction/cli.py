"""Extraction CLI for computing audio features and embeddings.

Examples
--------
Run every 10 seconds (default interval)::

    python -m sidetrack.extraction --schedule 10

Run on a cron schedule (every 5 minutes)::

    python -m sidetrack.extraction --schedule "*/5 * * * *"

The ``--schedule`` option accepts either a floating-point interval in seconds or a
standard cron expression. Cron expressions are validated before the extractor starts.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
import time
from datetime import UTC, datetime
from typing import Any

import typer
from croniter import croniter
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from sidetrack.config import ExtractionConfig, get_settings
from sidetrack.common.models import Track
from sidetrack.extraction.pipeline import analyze_track

app = typer.Typer(add_completion=False)


def get_db_url() -> str:
    settings = get_settings()
    return settings.db_url


def find_pending_tracks(db: Session, batch_size: int = 4) -> list[Track]:
    """Return tracks that have not yet been processed."""

    # Tracks with a local path and no features yet
    rows = db.execute(
        text(
            """
            SELECT t.track_id, t.title, t.path_local, t.duration
            FROM track t
            LEFT JOIN features f ON f.track_id = t.track_id
            WHERE t.path_local IS NOT NULL AND f.track_id IS NULL
            LIMIT :n
            """
        ),
        {"n": batch_size},
    ).all()
    out: list[Track] = []
    for tid, title, path_local, duration in rows:
        tr = Track()
        tr.track_id = tid
        tr.title = title
        tr.path_local = path_local
        tr.duration = duration
        out.append(tr)
    return out


@app.command()
def main(
    interval: float = typer.Option(
        10.0,
        "--interval",
        help="Seconds between extraction passes",
        envvar="EXTRACTOR_INTERVAL",
    ),
    schedule: str | None = typer.Option(
        None,
        "--schedule",
        help="Cron expression or seconds between passes",
        envvar="EXTRACTOR_SCHEDULE",
    ),
    once: bool = typer.Option(False, help="Run one pass then exit"),
    batch_size: int = typer.Option(4, help="Tracks to process per pass"),
) -> None:
    if schedule is not None:
        try:
            interval = float(schedule)
            if interval <= 0:
                raise ValueError
            schedule = None
        except ValueError:
            if not croniter.is_valid(schedule):
                raise typer.BadParameter("Schedule must be seconds or a cron expression")
    url = get_db_url()
    engine = create_engine(url, pool_pre_ping=True)
    typer.echo(f"[extraction] connected to DB: {url}")
    settings = get_settings()
    deadline = time.time() + float(settings.extractor_db_wait_secs)
    wait_interval = float(settings.extractor_db_wait_interval)
    while True:
        with Session(engine) as db:
            try:
                db.execute(text("SELECT 1 FROM track LIMIT 1"))
                break
            except Exception as e:
                if time.time() >= deadline:
                    typer.echo(f"[extraction] DB not ready after wait: {e}")
                    return
                typer.echo(f"[extraction] DB not ready: {e}")
        time.sleep(wait_interval)
    cfg = ExtractionConfig()
    cfg.set_seed(0)
    asyncio.run(_run_loop(engine, batch_size, interval, once, schedule, cfg))


async def _run_loop(
    engine: Any,
    batch_size: int,
    interval: float,
    once: bool,
    schedule: str | None,
    cfg: ExtractionConfig,
) -> None:
    stop_event = asyncio.Event()

    def _stop(*_: object) -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:  # pragma: no cover - windows
            signal.signal(sig, lambda *_: stop_event.set())

    try:
        while not stop_event.is_set():
            with Session(engine) as db:
                try:
                    pending = find_pending_tracks(db, batch_size=batch_size)
                except ProgrammingError as e:
                    typer.echo(f"[extraction] DB not ready during loop: {e}")
                    await asyncio.sleep(3)
                    continue
                if not pending:
                    typer.echo("[extraction] no pending tracks; sleeping")
                for tr in pending:
                    try:
                        analyze_track(tr.track_id, cfg)
                        ok = True
                    except Exception:  # pragma: no cover - refine in future
                        ok = False
                    typer.echo(f"[extraction] track {tr.track_id} analyzed: {ok}")
            if once:
                break
            if schedule:
                now = datetime.now(UTC)
                next_time = croniter(schedule, now).get_next(datetime)
                delay = (next_time - now).total_seconds()
            else:
                delay = interval
            sleep_task = asyncio.create_task(asyncio.sleep(delay))
            stop_task = asyncio.create_task(stop_event.wait())
            done, pending_tasks = await asyncio.wait(
                {sleep_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending_tasks:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
    finally:
        typer.echo("[extraction] stopping")


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    app()
