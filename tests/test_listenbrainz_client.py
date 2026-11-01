"""Spec: listening/listenbrainz-import, paging and rate limits, with a stubbed transport."""

import json
from pathlib import Path

import httpx
import pytest

from sidetrack.external import http, listenbrainz

pytestmark = pytest.mark.unit

PAGE = json.loads(
    (Path(__file__).parent / "fixtures/listenbrainz/page.json").read_text(encoding="utf-8")
)


@pytest.fixture
def transport(monkeypatch):
    requests, responses = [], []

    def handle(request):
        requests.append(request)
        return responses.pop(0) if responses else httpx.Response(200, json=PAGE)

    client = httpx.Client(transport=httpx.MockTransport(handle))
    monkeypatch.setattr(http, "_shared_client", client)
    monkeypatch.setattr(listenbrainz, "_resume_at", 0.0)
    return requests, responses


def test_requests_a_page_with_its_bounds(transport):
    requests, _ = transport
    listens = listenbrainz.get_listens("fixture listener", count=1000, max_ts=20)
    assert len(listens) == 3
    assert requests[0].url.raw_path.startswith(b"/1/user/fixture%20listener/listens?")
    assert dict(requests[0].url.params) == {"count": "1000", "max_ts": "20"}
    listenbrainz.get_listens("fixture", min_ts=10)
    assert dict(requests[1].url.params) == {"count": "1000", "min_ts": "10"}


def test_no_credential_is_sent(transport):
    requests, _ = transport
    listenbrainz.get_listens("fixture")
    assert "authorization" not in requests[0].headers


def test_waits_for_the_reset_when_the_allowance_is_spent(transport, monkeypatch):
    _, responses = transport
    now = [100.0]
    slept = []

    def sleep(seconds):
        slept.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(listenbrainz.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(listenbrainz.time, "sleep", sleep)
    responses.append(
        httpx.Response(
            200,
            json=PAGE,
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset-In": "5"},
        )
    )
    listenbrainz.get_listens("fixture")
    assert slept == []
    assert len(listenbrainz.get_listens("fixture")) == 3
    assert slept == [5.0]


def test_a_429_waits_for_the_reset_and_retries(transport, monkeypatch):
    requests, responses = transport
    now = [100.0]
    slept = []

    def sleep(seconds):
        slept.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(listenbrainz.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(listenbrainz.time, "sleep", sleep)
    monkeypatch.setattr(http.time, "sleep", sleep)
    responses.append(
        httpx.Response(429, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset-In": "7"})
    )
    assert len(listenbrainz.get_listens("fixture")) == 3
    assert len(requests) == 2
    assert sum(slept) >= 7
