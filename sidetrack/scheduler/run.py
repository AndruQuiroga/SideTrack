import logging
import time

import requests
import schedule

from .config import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("scheduler")

settings = get_settings()


def fetch_user_ids() -> list[str]:
    try:
        resp = requests.get(f"{settings.api_url}/auth/users", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            return data.get("users", [])
        return data
    except Exception:  # pragma: no cover - network errors
        logger.exception("fetch user ids error")
        return []


def ingest_listens():
    for user_id in fetch_user_ids():
        try:
            r = requests.post(
                f"{settings.api_url}/ingest/listens",
                timeout=10,
                headers={"X-User-Id": user_id},
            )
            logger.info("ingest listens %s: %s", user_id, r.status_code)
        except Exception:
            logger.exception("ingest listens error for %s", user_id)


def import_spotify_listens():
    for user_id in fetch_user_ids():
        try:
            r = requests.post(
                f"{settings.api_url}/spotify/listens",
                timeout=10,
                headers={"X-User-Id": user_id},
            )
            logger.info("spotify listens %s: %s", user_id, r.status_code)
        except Exception:
            logger.exception("spotify listens error for %s", user_id)


def sync_lastfm_tags():
    for user_id in fetch_user_ids():
        try:
            r = requests.post(
                f"{settings.api_url}/tags/lastfm/sync",
                timeout=10,
                headers={"X-User-Id": user_id},
            )
            logger.info("lastfm sync %s: %s", user_id, r.status_code)
        except Exception:
            logger.exception("lastfm sync error for %s", user_id)


def aggregate_weeks():
    for user_id in fetch_user_ids():
        try:
            r = requests.post(
                f"{settings.api_url}/aggregate/weeks",
                timeout=30,
                headers={"X-User-Id": user_id},
            )
            logger.info("aggregate weeks %s: %s", user_id, r.status_code)
        except Exception:
            logger.exception("aggregate weeks error for %s", user_id)


def schedule_jobs():
    ingest_minutes = settings.ingest_listens_interval_minutes
    spotify_minutes = settings.spotify_listens_interval_minutes
    tags_minutes = settings.lastfm_sync_interval_minutes
    agg_minutes = settings.aggregate_weeks_interval_minutes
    schedule.every(ingest_minutes).minutes.do(ingest_listens)
    schedule.every(spotify_minutes).minutes.do(import_spotify_listens)
    schedule.every(tags_minutes).minutes.do(sync_lastfm_tags)
    schedule.every(agg_minutes).minutes.do(aggregate_weeks)


def main():
    schedule_jobs()
    logger.info("started")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
