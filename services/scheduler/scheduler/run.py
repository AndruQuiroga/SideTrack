import time
import schedule
import requests
import logging

from .config import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("scheduler")

settings = get_settings()


def ingest_listens():
    try:
        r = requests.post(
            f"{settings.api_url}/ingest/listens",
            timeout=10,
            headers={"X-User-Id": settings.default_user_id},
        )
        logger.info("ingest listens: %s", r.status_code)
    except Exception:
        logger.exception("ingest listens error")


def sync_lastfm_tags():
    try:
        r = requests.post(
            f"{settings.api_url}/tags/lastfm/sync",
            timeout=10,
            headers={"X-User-Id": settings.default_user_id},
        )
        logger.info("lastfm sync: %s", r.status_code)
    except Exception:
        logger.exception("lastfm sync error")


def aggregate_weeks():
    try:
        r = requests.post(
            f"{settings.api_url}/aggregate/weeks",
            timeout=30,
            headers={"X-User-Id": settings.default_user_id},
        )
        logger.info("aggregate weeks: %s", r.status_code)
    except Exception:
        logger.exception("aggregate weeks error")


def schedule_jobs():
    ingest_minutes = settings.ingest_listens_interval_minutes
    tags_minutes = settings.lastfm_sync_interval_minutes
    agg_minutes = settings.aggregate_weeks_interval_minutes
    schedule.every(ingest_minutes).minutes.do(ingest_listens)
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

