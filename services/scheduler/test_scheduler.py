import pytest
import schedule

pytestmark = pytest.mark.unit


def test_all_jobs_run(monkeypatch):
    calls = []

    def fake_post(url, timeout=10, headers=None):
        calls.append((url, headers))

        class Resp:
            status_code = 200

            def json(self):
                return {}

        return Resp()

    monkeypatch.setenv("API_URL", "http://api")
    monkeypatch.setenv("INGEST_LISTENS_INTERVAL_MINUTES", "1")
    monkeypatch.setenv("SPOTIFY_LISTENS_INTERVAL_MINUTES", "1")
    monkeypatch.setenv("LASTFM_SYNC_INTERVAL_MINUTES", "1")
    monkeypatch.setenv("AGGREGATE_WEEKS_INTERVAL_MINUTES", "1")
    monkeypatch.setenv("DEFAULT_USER_ID", "u1")
    import importlib

    run = importlib.import_module("sidetrack.scheduler.run")
    monkeypatch.setattr(run.requests, "post", fake_post)

    schedule.clear()
    run.schedule_jobs()
    schedule.run_all(delay_seconds=0)

    expected_headers = {"X-User-Id": "u1"}
    assert ("http://api/ingest/listens", expected_headers) in calls
    assert ("http://api/spotify/listens", expected_headers) in calls
    assert ("http://api/tags/lastfm/sync", expected_headers) in calls
    assert ("http://api/aggregate/weeks", expected_headers) in calls
