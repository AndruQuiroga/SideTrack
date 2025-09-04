import os
import time
import schedule
import requests

API = os.getenv("API_URL", "http://api:8000")


def job():
    try:
        r = requests.get(f"{API}/health", timeout=5)
        print("[scheduler] health:", r.json())
    except Exception as e:
        print("[scheduler] error:", e)


def main():
    schedule.every(1).minutes.do(job)
    print("[scheduler] started")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()

