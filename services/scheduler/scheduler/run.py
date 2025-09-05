import os
import time
import schedule
import requests

API = os.getenv("API_URL", "http://api:8000")
user_id = os.getenv("DEFAULT_USER_ID")


def ingest_listens():
    try:
        r = requests.post(
            f"{API}/ingest/listens",
            timeout=10,
            headers={"X-User-Id": user_id},
        )
        print("[scheduler] ingest listens:", r.status_code)
    except Exception as e:
        print("[scheduler] ingest listens error:", e)


def sync_lastfm_tags():
    try:
        r = requests.post(
            f"{API}/tags/lastfm/sync",
            timeout=10,
            headers={"X-User-Id": user_id},
        )
        print("[scheduler] lastfm sync:", r.status_code)
    except Exception as e:
        print("[scheduler] lastfm sync error:", e)


def aggregate_weeks():
    try:
        r = requests.post(
            f"{API}/aggregate/weeks",
            timeout=30,
            headers={"X-User-Id": user_id},
        )
        print("[scheduler] aggregate weeks:", r.status_code)
    except Exception as e:
        print("[scheduler] aggregate weeks error:", e)


def schedule_jobs():
    ingest_minutes = float(os.getenv("INGEST_LISTENS_INTERVAL_MINUTES", "1"))
    tags_minutes = float(os.getenv("LASTFM_SYNC_INTERVAL_MINUTES", "30"))
    agg_minutes = float(os.getenv("AGGREGATE_WEEKS_INTERVAL_MINUTES", str(60 * 24)))
    schedule.every(ingest_minutes).minutes.do(ingest_listens)
    schedule.every(tags_minutes).minutes.do(sync_lastfm_tags)
    schedule.every(agg_minutes).minutes.do(aggregate_weeks)


def main():
    schedule_jobs()
    print("[scheduler] started")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()

