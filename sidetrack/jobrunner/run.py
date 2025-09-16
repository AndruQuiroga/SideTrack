"""Lightweight job runner that enqueues jobs for asynchronous execution."""

from __future__ import annotations

import logging
import time
import warnings
from datetime import date, datetime

import redis
import schedule
from rq import Queue
from sqlalchemy import select

from sidetrack.api.db import SessionLocal
from sidetrack.common.logging import setup_logging
from sidetrack.common.models import UserAccount
from sidetrack.worker import jobs as worker_jobs

from .config import get_settings

logger = logging.getLogger("sidetrack.jobrunner")

settings = get_settings()
connection = redis.from_url(settings.redis_url)
queue = Queue("analysis", connection=connection)

# In-memory state tracking
JOB_STATE: dict[tuple[str, str], dict] = {}
CURSORS: dict[tuple[str, str], str] = {}


def fetch_user_ids() -> list[str]:
    """Return all registered user ids from the database."""
    try:
        with SessionLocal(async_session=False) as db:
            stmt = select(UserAccount.user_id)
            return list(db.execute(stmt).scalars().all())
    except Exception:  # pragma: no cover - db errors
        logger.exception("fetch user ids error")
        return []


def _enqueue_job(user_id: str, job_type: str, func) -> None:
    key = (user_id, job_type)
    cursor = CURSORS.get(key)
    try:
        queue.enqueue(func, user_id, cursor)
        status = "queued"
        CURSORS[key] = date.today().isoformat()
    except Exception:
        logger.exception("%s enqueue error for %s", job_type, user_id)
        status = "error"
    JOB_STATE[key] = {"last_status": status, "last_run": datetime.utcnow()}


def sync_user(user_id: str) -> None:
    _enqueue_job(user_id, "sync:user", worker_jobs.sync_user)


def aggregate_weeks(user_id: str) -> None:
    _enqueue_job(user_id, "aggregate:weeks", worker_jobs.aggregate_weeks)


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


def main() -> None:
    setup_logging()
    schedule_jobs()
    logger.info("started")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    warnings.warn(
        "`python -m sidetrack.jobrunner.run` is deprecated; use "
        "`python -m sidetrack schedule` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    main()
