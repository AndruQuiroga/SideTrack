import sys
import pathlib
import schedule

# ensure we can import scheduler.run
sys.path.append(str(pathlib.Path(__file__).resolve().parent))


def test_all_jobs_run(monkeypatch):
    calls = []

    def fake_post(url, timeout=10):
        calls.append(url)
        class Resp:
            status_code = 200
            def json(self):
                return {}
        return Resp()

    monkeypatch.setenv("API_URL", "http://api")
    monkeypatch.setenv("INGEST_LISTENS_INTERVAL_MINUTES", "1")
    monkeypatch.setenv("LASTFM_SYNC_INTERVAL_MINUTES", "1")
    monkeypatch.setenv("AGGREGATE_WEEKS_INTERVAL_MINUTES", "1")

    import importlib
    run = importlib.import_module("scheduler.run")
    monkeypatch.setattr(run.requests, "post", fake_post)

    schedule.clear()
    run.schedule_jobs()
    schedule.run_all(delay_seconds=0)

    assert "http://api/ingest/listens" in calls
    assert "http://api/tags/lastfm/sync" in calls
    assert "http://api/aggregate/weeks" in calls
