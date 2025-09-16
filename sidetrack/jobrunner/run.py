"""Lightweight job runner that enqueues jobs for asynchronous execution."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import warnings
from datetime import date, datetime
from typing import Iterable, Any

import redis
import schedule
from redis.exceptions import RedisError
from rq import Queue
from rq.job import Job
from rq.registry import DeferredJobRegistry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.api.db import SessionLocal
from sidetrack.common.logging import setup_logging
from sidetrack.common.models import UserAccount
from sidetrack.worker import jobs as worker_jobs

from .config import Settings, get_settings

logger = logging.getLogger("sidetrack.jobrunner")

settings = get_settings()
connection = redis.from_url(settings.redis_url)
queue = Queue("analysis", connection=connection)

STATE_HASH = "sidetrack:jobrunner:state"
CURSOR_HASH = "sidetrack:jobrunner:cursors"
LAST_JOB_HASH = "sidetrack:jobrunner:last-job"


def _hash_key(user_id: str, job_type: str) -> str:
    return f"{user_id}:{job_type}"


def _decode(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _load_state(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(_decode(raw))
    except (TypeError, json.JSONDecodeError):  # pragma: no cover - defensive
        return {}
    last_run = data.get("last_run")
    if last_run:
        try:
            data["last_run"] = datetime.fromisoformat(last_run)
        except ValueError:  # pragma: no cover - defensive
            data["last_run"] = None
    else:
        data["last_run"] = None
    return data


def get_job_state(user_id: str, job_type: str) -> dict[str, Any]:
    """Return persisted metadata for the scheduled job."""

    key = _hash_key(user_id, job_type)
    try:
        raw = queue.connection.hget(STATE_HASH, key)
    except RedisError:  # pragma: no cover - redis failure
        logger.exception("job state fetch error for %s", key)
        return {}
    return _load_state(raw)


def _store_state(user_id: str, job_type: str, status: str, when: datetime | None) -> None:
    payload = {
        "last_status": status,
        "last_run": when.isoformat() if when else None,
    }
    key = _hash_key(user_id, job_type)
    try:
        queue.connection.hset(STATE_HASH, key, json.dumps(payload))
    except RedisError:  # pragma: no cover - redis failure
        logger.exception("job state store error for %s", key)


def _get_cursor(user_id: str, job_type: str) -> str | None:
    key = _hash_key(user_id, job_type)
    try:
        value = queue.connection.hget(CURSOR_HASH, key)
    except RedisError:  # pragma: no cover - redis failure
        logger.exception("cursor fetch error for %s", key)
        return None
    return _decode(value) if value else None


def _store_cursor(user_id: str, job_type: str, cursor: str) -> None:
    key = _hash_key(user_id, job_type)
    try:
        queue.connection.hset(CURSOR_HASH, key, cursor)
    except RedisError:  # pragma: no cover - redis failure
        logger.exception("cursor store error for %s", key)


def _get_last_job(user_id: str, job_type: str) -> Job | None:
    key = _hash_key(user_id, job_type)
    try:
        job_id = queue.connection.hget(LAST_JOB_HASH, key)
    except RedisError:  # pragma: no cover - redis failure
        logger.exception("last job fetch error for %s", key)
        return None
    if not job_id:
        return None
    job = queue.fetch_job(_decode(job_id))
    if job is None:
        try:
            queue.connection.hdel(LAST_JOB_HASH, key)
        except RedisError:  # pragma: no cover - redis failure
            logger.exception("last job cleanup error for %s", key)
    return job


def _store_last_job(user_id: str, job_type: str, job: Job) -> None:
    key = _hash_key(user_id, job_type)
    try:
        queue.connection.hset(LAST_JOB_HASH, key, job.id)
    except RedisError:  # pragma: no cover - redis failure
        logger.exception("last job store error for %s", key)


def _job_timestamp(job: Job, status: str) -> datetime | None:
    if status == "started":
        return job.started_at or job.enqueued_at
    if status in {"finished", "failed"}:
        return job.ended_at or job.enqueued_at
    if status == "deferred":
        registry = DeferredJobRegistry(queue.name, connection=queue.connection)
        if job.id in registry:
            return job.enqueued_at
    return job.enqueued_at


async def fetch_user_ids_async(db: AsyncSession | None = None) -> list[str]:
    """Return all registered user ids using an async SQLAlchemy session."""

    async def _run(session: AsyncSession) -> list[str]:
        try:
            result = await session.execute(select(UserAccount.user_id))
            return list(result.scalars().all())
        except Exception:  # pragma: no cover - db errors
            logger.exception("fetch user ids error")
            return []

    if db is not None:
        return await _run(db)

    async with SessionLocal(async_session=True) as session:  # type: ignore[arg-type]
        return await _run(session)


def fetch_user_ids() -> list[str]:
    """Synchronous wrapper for :func:`fetch_user_ids_async`."""

    return asyncio.run(fetch_user_ids_async())


def _enqueue_job(user_id: str, job_type: str, func) -> None:
    job = _get_last_job(user_id, job_type)
    if job is not None:
        status = job.get_status(refresh=True)
        timestamp = _job_timestamp(job, status)
        _store_state(user_id, job_type, status, timestamp)
        if status in {"queued", "started", "deferred"}:
            return

    cursor = _get_cursor(user_id, job_type)
    try:
        job = queue.enqueue(func, user_id, cursor)
    except Exception:
        logger.exception("%s enqueue error for %s", job_type, user_id)
        _store_state(user_id, job_type, "error", datetime.utcnow())
        return

    _store_last_job(user_id, job_type, job)
    _store_cursor(user_id, job_type, date.today().isoformat())
    _store_state(user_id, job_type, "queued", job.enqueued_at or datetime.utcnow())


def sync_user(user_id: str) -> None:
    _enqueue_job(user_id, "sync:user", worker_jobs.sync_user)


def aggregate_weeks(user_id: str) -> None:
    _enqueue_job(user_id, "aggregate:weeks", worker_jobs.aggregate_weeks)


def generate_weekly_insights(user_id: str) -> None:
    _enqueue_job(user_id, "insights:weekly", worker_jobs.generate_weekly_insights)


def _schedule_for_users(user_ids: Iterable[str], settings: Settings) -> None:
    """Register scheduler jobs for ``user_ids`` using provided settings."""

    schedule.clear()
    sync_minutes = settings.ingest_listens_interval_minutes
    agg_minutes = settings.aggregate_weeks_interval_minutes
    insights_minutes = settings.weekly_insights_interval_minutes

    for user_id in user_ids:
        schedule.every(sync_minutes).minutes.do(sync_user, user_id).tag(
            f"id:{user_id}:sync:user", f"user:{user_id}", "job:sync:user"
        )
        schedule.every(agg_minutes).minutes.do(aggregate_weeks, user_id).tag(
            f"id:{user_id}:aggregate:weeks", f"user:{user_id}", "job:aggregate:weeks"
        )
        schedule.every(insights_minutes).minutes.do(generate_weekly_insights, user_id).tag(
            f"id:{user_id}:insights:weekly", f"user:{user_id}", "job:insights:weekly"
        )


async def schedule_jobs_async() -> None:
    """Async variant that initialises scheduled jobs."""

    settings = get_settings()
    user_ids = await fetch_user_ids_async()
    _schedule_for_users(user_ids, settings)


def schedule_jobs() -> None:
    """Schedule periodic tasks for each registered user."""

    settings = get_settings()
    user_ids = fetch_user_ids()
    _schedule_for_users(user_ids, settings)


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
