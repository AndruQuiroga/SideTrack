"""Lightweight scheduler that triggers API tasks for all users."""

import logging
import time

import requests
import schedule
from sqlalchemy import select

from sidetrack.api.db import SessionLocal
from sidetrack.common.models import UserAccount

from .config import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("scheduler")

settings = get_settings()


def fetch_user_ids() -> list[str]:
    """Return all registered user ids from the database."""
    try:
        with SessionLocal(async_session=False) as db:
            stmt = select(UserAccount.user_id)
            return list(db.execute(stmt).scalars().all())
    except Exception:  # pragma: no cover - db errors
        logger.exception("fetch user ids error")
        return []


def ingest_listens(user_id: str) -> None:
    """Trigger ListenBrainz ingestion for ``user_id``."""
    try:
        r = requests.post(
            f"{settings.api_url}/ingest/listens",
            timeout=10,
            headers={"X-User-Id": user_id},
        )
        logger.info("ingest listens %s: %s", user_id, r.status_code)
    except Exception:
        logger.exception("ingest listens error for %s", user_id)


def import_spotify_listens(user_id: str) -> None:
    """Trigger Spotify listens import for ``user_id``."""
    try:
        r = requests.post(
            f"{settings.api_url}/spotify/listens",
            timeout=10,
            headers={"X-User-Id": user_id},
        )
        logger.info("spotify listens %s: %s", user_id, r.status_code)
    except Exception:
        logger.exception("spotify listens error for %s", user_id)


def sync_lastfm_tags(user_id: str) -> None:
    """Trigger Last.fm tag sync for ``user_id``."""
    try:
        r = requests.post(
            f"{settings.api_url}/tags/lastfm/sync",
            timeout=10,
            headers={"X-User-Id": user_id},
        )
        logger.info("lastfm sync %s: %s", user_id, r.status_code)
    except Exception:
        logger.exception("lastfm sync error for %s", user_id)


def aggregate_weeks(user_id: str) -> None:
    """Trigger weekly aggregation for ``user_id``."""
    try:
        r = requests.post(
            f"{settings.api_url}/aggregate/weeks",
            timeout=30,
            headers={"X-User-Id": user_id},
        )
        logger.info("aggregate weeks %s: %s", user_id, r.status_code)
    except Exception:
        logger.exception("aggregate weeks error for %s", user_id)


def schedule_jobs() -> None:
    """Schedule periodic tasks for each registered user."""
    ingest_minutes = settings.ingest_listens_interval_minutes
    spotify_minutes = settings.spotify_listens_interval_minutes
    tags_minutes = settings.lastfm_sync_interval_minutes
    agg_minutes = settings.aggregate_weeks_interval_minutes

    for user_id in fetch_user_ids():
        schedule.every(ingest_minutes).minutes.do(ingest_listens, user_id)
        schedule.every(spotify_minutes).minutes.do(import_spotify_listens, user_id)
        schedule.every(tags_minutes).minutes.do(sync_lastfm_tags, user_id)
        schedule.every(agg_minutes).minutes.do(aggregate_weeks, user_id)


def main():
    schedule_jobs()
    logger.info("started")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
