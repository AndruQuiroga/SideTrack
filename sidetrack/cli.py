"""Unified command line interface for SideTrack services."""

from __future__ import annotations

import asyncio
import os
from datetime import date, datetime
from typing import Optional

import click
import typer
from typer.core import TyperOption
from typer import rich_utils as typer_rich_utils


_ORIG_MAKE_METAVAR = TyperOption.make_metavar


def _typer_option_make_metavar(self: TyperOption, ctx: click.Context | None = None) -> str:
    if ctx is None:
        ctx = click.Context(click.Command(self.name or "sidetrack"))
    return _ORIG_MAKE_METAVAR(self, ctx)


TyperOption.make_metavar = _typer_option_make_metavar  # type: ignore[assignment]


def _rich_format_help(
    ctx: click.Context, formatter: click.HelpFormatter, *_args: object, **_kwargs: object
) -> str:
    ctx.command.format_help(ctx, formatter)
    return formatter.getvalue().rstrip("\n")


typer_rich_utils.rich_format_help = _rich_format_help  # type: ignore[assignment]


app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode=None,
    help="SideTrack command line interface.",
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Top-level callback executed before subcommands."""


def _parse_since(value: Optional[str]) -> Optional[datetime]:
    """Parse ``value`` into a :class:`datetime` when provided."""

    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - user input branch
        raise typer.BadParameter(
            "Expected ISO 8601 date or datetime, e.g. 2024-01-01 or 2024-01-01T12:00"
        ) from exc


ingest_app = typer.Typer(
    add_completion=False,
    help="Utilities for fetching and ingesting listens.",
)


@ingest_app.command("lastfm", help="Fetch listens from Last.fm and ingest them into the database.")
def ingest_lastfm(
    user: str = typer.Option(..., "--user", help="Last.fm username to fetch."),
    as_user: Optional[str] = typer.Option(
        None,
        "--as-user",
        help="Override the target SideTrack user id (defaults to the Last.fm username).",
    ),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        help="Earliest listen timestamp to fetch (ISO 8601 date or datetime).",
    ),
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        help="Override DATABASE_URL for this invocation.",
    ),
) -> None:
    """Ingest recent listens for ``user`` from Last.fm."""

    from sidetrack.api.config import get_settings
    from sidetrack.services.ingestion import get_ingester

    if database_url:
        os.environ["DATABASE_URL"] = database_url
        get_settings.cache_clear()

    since_dt = _parse_since(since)

    settings = get_settings()
    ingester = get_ingester("lastfm", api_key=settings.lastfm_api_key)
    created = asyncio.run(
        ingester.ingest(lastfm_user=user, as_user=as_user, since=since_dt)
    )

    typer.echo(
        f"Ingested {created} listens from Last.fm for {user} → user={as_user or user}"
    )


app.add_typer(ingest_app, name="ingest")


@app.command("extract", help="Audio feature extraction tools.")
def extract(
    interval: float = typer.Option(
        10.0,
        "--interval",
        help="Seconds between extraction passes",
        envvar="EXTRACTOR_INTERVAL",
    ),
    schedule: Optional[str] = typer.Option(
        None,
        "--schedule",
        help="Cron expression or seconds between passes",
        envvar="EXTRACTOR_SCHEDULE",
    ),
    once: bool = typer.Option(False, help="Run one pass then exit"),
    batch_size: int = typer.Option(4, help="Tracks to process per pass"),
) -> None:
    from sidetrack.extraction.cli import main as extraction_main

    extraction_main(
        interval=interval,
        schedule=schedule,
        once=once,
        batch_size=batch_size,
    )


@app.command("schedule", help="Start the periodic job scheduler.")
def schedule() -> None:
    """Run the lightweight job scheduler."""

    from sidetrack.jobrunner.run import main as jobrunner_main

    jobrunner_main()


worker_app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Worker process management and job utilities.",
)


@worker_app.command("run", help="Start the RQ worker process.")
def worker_run() -> None:
    """Launch the worker that consumes queued jobs."""

    from sidetrack.worker.run import main as worker_main

    worker_main()


jobs_app = typer.Typer(
    add_completion=False,
    help="Execute worker jobs manually.",
)


@jobs_app.command("sync-user", help="Synchronise listens for a user across providers.")
def worker_sync_user(
    user_id: str = typer.Argument(..., help="Target SideTrack user id."),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        help="Earliest date to sync listens (YYYY-MM-DD).",
    ),
) -> None:
    from sidetrack.worker.jobs import sync_user

    cursor = None
    if since:
        try:
            cursor = date.fromisoformat(since).isoformat()
        except ValueError as exc:  # pragma: no cover - user input branch
            raise typer.BadParameter("--since must be in YYYY-MM-DD format") from exc
    sync_user(user_id, cursor)
    typer.echo(f"Completed sync_user job for {user_id}")


@jobs_app.command("aggregate-weeks", help="Aggregate weekly insights for a user.")
def worker_aggregate_weeks(
    user_id: str = typer.Argument(..., help="Target SideTrack user id."),
) -> None:
    from sidetrack.worker.jobs import aggregate_weeks

    aggregate_weeks(user_id)
    typer.echo(f"Completed aggregate_weeks job for {user_id}")


@jobs_app.command("weekly-insights", help="Generate weekly insight events for a user.")
def worker_weekly_insights(
    user_id: str = typer.Argument(..., help="Target SideTrack user id."),
) -> None:
    from sidetrack.worker.jobs import generate_weekly_insights

    count = generate_weekly_insights(user_id)
    typer.echo(f"Generated {count} weekly insight events for {user_id}")


worker_app.add_typer(jobs_app, name="jobs")
app.add_typer(worker_app, name="worker")


__all__ = ["app"]
