"""Lightweight scheduler that triggers API tasks for all users."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import date, datetime

import httpx
import schedule
from sqlalchemy import select

from sidetrack.api.clients.lastfm import LastfmClient
from sidetrack.api.db import SessionLocal
from sidetrack.api.main import aggregate_weeks as aggregate_weeks_service
from sidetrack.api.services.listen_service import get_listen_service
from sidetrack.common.models import UserAccount
from sidetrack.services.datasync import sync_user as datasync_sync_user
from sidetrack.services.listenbrainz import ListenBrainzClient
from sidetrack.services.musicbrainz import MusicBrainzService
from sidetrack.services.spotify import SpotifyClient

from .config import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("scheduler")

# In-memory state tracking
JOB_STATE: dict[tuple[str, str], dict] = {}
CURSORS: dict[tuple[str, str], str] = {}
LOCKS: dict[tuple[str, str], threading.Lock] = {}


def fetch_user_ids() -> list[str]:
    """Return all registered user ids from the database."""
    try:
        with SessionLocal(async_session=False) as db:
            stmt = select(UserAccount.user_id)
            return list(db.execute(stmt).scalars().all())
    except Exception:  # pragma: no cover - db errors
        logger.exception("fetch user ids error")
        return []


async def _sync_user_service(user_id: str, since: date | None, db) -> None:
    settings = get_settings()
    listen_service = get_listen_service(db)
    rate = settings.lastfm_rate_limit or 5.0
    min_interval = 1.0 / rate if rate > 0 else 0.0
    async with (
        httpx.AsyncClient() as lb_http,
        httpx.AsyncClient() as lf_http,
        httpx.AsyncClient() as sp_http,
        httpx.AsyncClient() as mb_http,
    ):
        lb_client = ListenBrainzClient(lb_http)
        lf_client = LastfmClient(
            lf_http,
            settings.lastfm_api_key,
            settings.lastfm_api_secret,
            min_interval=min_interval,
        )
        sp_client = SpotifyClient(
            sp_http, settings.spotify_client_id, settings.spotify_client_secret
        )
        mb_service = MusicBrainzService(mb_http)
        await datasync_sync_user(
            user_id,
            db=db,
            listen_service=listen_service,
            lb_client=lb_client,
            lf_client=lf_client,
            sp_client=sp_client,
            mb_service=mb_service,
            settings=settings,
            since=since,
        )


async def _aggregate_weeks_service(user_id: str, _since: date | None, db) -> None:
    await aggregate_weeks_service(db=db, user_id=user_id)


def _run_job(user_id: str, job_type: str, func) -> None:
    key = (user_id, job_type)
    lock = LOCKS.setdefault(key, threading.Lock())
    if not lock.acquire(blocking=False):
        return

    cursor = CURSORS.get(key)
    since = date.fromisoformat(cursor) if cursor else None

    async def runner():
        async with SessionLocal() as db:
            await func(user_id, since, db)

    try:
        asyncio.run(runner())
        status = "ok"
        CURSORS[key] = date.today().isoformat()
    except Exception:
        logger.exception("%s error for %s", job_type, user_id)
        status = "error"
    finally:
        lock.release()

    JOB_STATE[key] = {"last_status": status, "last_run": datetime.utcnow()}


def sync_user(user_id: str) -> None:
    _run_job(user_id, "sync:user", _sync_user_service)


def aggregate_weeks(user_id: str) -> None:
    _run_job(user_id, "aggregate:weeks", _aggregate_weeks_service)


def schedule_jobs() -> None:
    """Schedule periodic tasks for each registered user."""
    schedule.clear()
    settings = get_settings()
    sync_minutes = settings.ingest_listens_interval_minutes
    agg_minutes = settings.aggregate_weeks_interval_minutes

    for user_id in fetch_user_ids():
        schedule.every(sync_minutes).minutes.do(sync_user, user_id).tag(
            f"id:{user_id}:sync:user", f"user:{user_id}", "job:sync:user"
        )
        schedule.every(agg_minutes).minutes.do(aggregate_weeks, user_id).tag(
            f"id:{user_id}:aggregate:weeks", f"user:{user_id}", "job:aggregate:weeks"
        )


def main():
    schedule_jobs()
    logger.info("started")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
