"""Worker entry point — APScheduler for periodic tasks + RQ for async jobs.

Run with: python -m services.worker
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from rq import Queue
from rq import Worker as RQWorker

from services.api.db import get_db, init_engine
from services.api.models import ProviderType

from .config import get_settings
from .connectors.spotify import SpotifyConnector
from .jobs.populate_features import populate_features
from .listen_store import ListenEventStore
from .sync import SyncCoordinator

logger = logging.getLogger(__name__)

# ── Globals (set during init) ──────────────────────────────────────

_coordinator: SyncCoordinator | None = None


# ── Scheduled tasks ────────────────────────────────────────────────


async def task_full_sync() -> None:
    """Periodic task: sync recent listens for all users."""
    if not _coordinator:
        return
    db = next(get_db())
    try:
        await _coordinator.run_full_sync(db)
    except Exception:
        logger.exception("Full sync failed")
    finally:
        db.close()


async def task_now_playing() -> None:
    """Periodic task: sweep now-playing for all users."""
    if not _coordinator:
        return
    db = next(get_db())
    try:
        await _coordinator.run_now_playing_sweep(db)
    except Exception:
        logger.exception("Now-playing sweep failed")
    finally:
        db.close()


async def task_populate_features() -> None:
    """Periodic task: fetch Spotify audio features for tracks missing them."""
    settings = get_settings()
    spotify = SpotifyConnector(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
    )
    db = next(get_db())
    try:
        await populate_features(db, spotify)
    except Exception:
        logger.exception("Feature population failed")
    finally:
        db.close()
        await spotify.close()


# ── Health server ──────────────────────────────────────────────────


def _start_health_server(port: int) -> None:
    """Start a simple HTTP health/status server in a daemon thread."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            status = _coordinator.status() if _coordinator else {}
            body = json.dumps(status, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            pass  # suppress access logs

    server = HTTPServer(("0.0.0.0", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Health/status server running on :%d", port)


# ── RQ worker thread ──────────────────────────────────────────────


def _start_rq_worker(redis_url: str) -> None:
    """Run the RQ worker in a daemon thread so it shares this process."""
    conn = redis.from_url(redis_url)
    queue = Queue("default", connection=conn)
    worker = RQWorker([queue], connection=conn)

    thread = threading.Thread(target=worker.work, kwargs={"with_scheduler": False}, daemon=True)
    thread.start()
    logger.info("RQ worker started in background thread")


# ── Main ───────────────────────────────────────────────────────────


async def _run() -> None:
    global _coordinator  # noqa: PLW0603

    settings = get_settings()

    # Logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )

    # Database
    init_engine(settings.database_url)

    # Build connector registry
    disabled: set[ProviderType] = set()
    if not settings.enable_spotify:
        disabled.add(ProviderType.SPOTIFY)
    if not settings.enable_lastfm:
        disabled.add(ProviderType.LASTFM)
    if not settings.enable_listenbrainz:
        disabled.add(ProviderType.LISTENBRAINZ)

    spotify = SpotifyConnector(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
    )
    connectors = {ProviderType.SPOTIFY: spotify}
    # Last.fm and ListenBrainz are handled by RQ jobs dispatched by the API,
    # not by the worker's sync loop. No connector needed here.

    store = ListenEventStore()
    _coordinator = SyncCoordinator(
        store=store,
        connectors=connectors,
        disabled_providers=disabled,
    )

    # Health endpoint
    _start_health_server(settings.status_port)

    # RQ worker (for existing async jobs like Last.fm ingest, taste recompute)
    _start_rq_worker(settings.redis_url)

    # APScheduler
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        task_full_sync,
        "interval",
        minutes=settings.sync_interval_minutes,
        id="full_sync",
        name="Sync recent listens for all users",
    )

    if settings.enable_now_playing:
        scheduler.add_job(
            task_now_playing,
            "interval",
            seconds=settings.now_playing_interval_seconds,
            id="now_playing",
            name="Now-playing sweep",
        )

    scheduler.add_job(
        task_populate_features,
        "interval",
        minutes=settings.feature_populate_interval_minutes,
        id="populate_features",
        name="Populate Spotify audio features",
    )

    scheduler.start()
    logger.info(
        "Worker started — sync=%dm, now_playing=%ds (enabled=%s), features=%dm",
        settings.sync_interval_minutes,
        settings.now_playing_interval_seconds,
        settings.enable_now_playing,
        settings.feature_populate_interval_minutes,
    )

    # Run initial tasks immediately
    await task_full_sync()
    if settings.enable_now_playing:
        await task_now_playing()
    await task_populate_features()

    # Keep alive
    stop_event = asyncio.Event()

    def _signal_handler(*_: object) -> None:
        logger.info("Shutting down...")
        scheduler.shutdown(wait=False)
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _signal_handler)

    await stop_event.wait()
    await spotify.close()


def main() -> None:
    """Sync entry point."""
    asyncio.run(_run())


if __name__ == "__main__":
    main()
