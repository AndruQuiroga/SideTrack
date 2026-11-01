"""ListenBrainz public listens API. Reads a public user's listens without a credential."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import quote

import httpx

from .http import request_json

BASE_URL = "https://api.listenbrainz.org/1"
HEADERS = {"User-Agent": "sidetrack/0.1 (personal listening history import)"}
MAX_PAGE = 1000

_resume_at = 0.0


def _note_limit(response: httpx.Response) -> None:
    """Remember when an exhausted allowance resets; ListenBrainz sends this on every response."""

    global _resume_at
    remaining = response.headers.get("X-RateLimit-Remaining")
    reset_in = response.headers.get("X-RateLimit-Reset-In")
    if remaining is None or reset_in is None:
        return
    if int(remaining) <= 0 or response.status_code == 429:
        _resume_at = time.monotonic() + float(reset_in)


@contextmanager
def _within_limit() -> Iterator[None]:
    wait = _resume_at - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    yield


def get_listens(
    username: str,
    *,
    count: int = MAX_PAGE,
    max_ts: int | None = None,
    min_ts: int | None = None,
) -> list[dict[str, Any]]:
    """One page, newest first. Both bounds are exclusive.

    With only ``max_ts`` the page holds the listens just before it; with only ``min_ts``,
    the listens just after it (observed 2026-10-31, design.md).
    """

    params: dict[str, int] = {"count": count}
    if max_ts is not None:
        params["max_ts"] = max_ts
    if min_ts is not None:
        params["min_ts"] = min_ts
    body = request_json(
        "ListenBrainz",
        "GET",
        f"{BASE_URL}/user/{quote(username, safe='')}/listens",
        params=params,
        headers=HEADERS,
        timeout=30.0,
        request_guard=_within_limit,
        on_response=_note_limit,
    )
    listens: list[dict[str, Any]] = body["payload"]["listens"]
    return listens
