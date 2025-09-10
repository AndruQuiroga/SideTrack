"""Lightweight scheduler that triggers API tasks for all users."""

from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime

import requests
import schedule
from sqlalchemy import select

from sidetrack.api.db import SessionLocal
from sidetrack.common.models import UserAccount

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


def _run_job(user_id: str, job_type: str, url: str) -> None:
    key = (user_id, job_type)
    lock = LOCKS.setdefault(key, threading.Lock())
    if not lock.acquire(blocking=False):
        return

    params: dict[str, str] | None = None
    cursor = CURSORS.get(key)
    if cursor:
        params = {"since": cursor}

    try:
        kwargs = {"timeout": 10, "headers": {"X-User-Id": user_id}}
        if params:
            kwargs["params"] = params
        r = requests.post(url, **kwargs)
        status = "ok" if r.status_code < 400 else f"http {r.status_code}"
        CURSORS[key] = date.today().isoformat()
    except Exception:
        logger.exception("%s error for %s", job_type, user_id)
        status = "error"
    finally:
        lock.release()

    JOB_STATE[key] = {"last_status": status, "last_run": datetime.utcnow()}


def ingest_listens(user_id: str) -> None:
    settings = get_settings()
    _run_job(user_id, "ingest:listens", f"{settings.api_url}/ingest/listens")


def sync_lastfm_tags(user_id: str) -> None:
    settings = get_settings()
    _run_job(user_id, "sync:tags", f"{settings.api_url}/tags/lastfm/sync")


def enrich_ids(user_id: str) -> None:
    settings = get_settings()
    _run_job(user_id, "enrich:ids", f"{settings.api_url}/enrich/ids")


def aggregate_weeks(user_id: str) -> None:
    settings = get_settings()
    _run_job(user_id, "aggregate:weeks", f"{settings.api_url}/aggregate/weeks")


def schedule_jobs() -> None:
    """Schedule periodic tasks for each registered user."""
    schedule.clear()
    settings = get_settings()
    ingest_minutes = settings.ingest_listens_interval_minutes
    tags_minutes = settings.lastfm_sync_interval_minutes
    enrich_minutes = settings.enrich_ids_interval_minutes
    agg_minutes = settings.aggregate_weeks_interval_minutes

    for user_id in fetch_user_ids():
        schedule.every(ingest_minutes).minutes.do(ingest_listens, user_id).tag(
            f"id:{user_id}:ingest:listens", f"user:{user_id}", "job:ingest:listens"
        )
        schedule.every(tags_minutes).minutes.do(sync_lastfm_tags, user_id).tag(
            f"id:{user_id}:sync:tags", f"user:{user_id}", "job:sync:tags"
        )
        schedule.every(enrich_minutes).minutes.do(enrich_ids, user_id).tag(
            f"id:{user_id}:enrich:ids", f"user:{user_id}", "job:enrich:ids"
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
