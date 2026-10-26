"""HTTP helpers with retries and User-Agent for external APIs.

Uses a module-level httpx.Client for connection pooling across requests.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager, nullcontext
from typing import Any

import httpx

# Module-level client for connection pooling.  Created lazily to avoid
# import-time side effects; closed explicitly at shutdown if needed.
_shared_client: httpx.Client | None = None


def _get_client(timeout: float = 15.0) -> httpx.Client:
    """Return (or create) the shared httpx.Client with connection pooling."""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.Client(timeout=timeout)
    return _shared_client


def close_client() -> None:
    """Explicitly close the shared client (e.g. on app shutdown)."""
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        _shared_client.close()
        _shared_client = None


class ExternalApiError(RuntimeError):
    def __init__(self, service: str, status: int, url: str, body: Any | None = None):
        super().__init__(f"{service} returned HTTP {status} for {url}")
        self.service = service
        self.status = status
        self.url = url
        self.body = body


def _retry_delays(max_attempts: int) -> list[float]:
    return [0.0] + [min(2**i * 0.25, 3.0) for i in range(1, max_attempts)]


def request_json(
    service: str,
    method: str,
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = 15.0,
    max_attempts: int = 3,
    request_guard: Callable[[], AbstractContextManager] | None = None,
) -> Any:
    h = dict(headers or {})
    delays = _retry_delays(max_attempts)
    last_exc: Exception | None = None
    client = _get_client(timeout)

    for attempt, delay in enumerate(delays, start=1):
        if delay:
            # NOTE: time.sleep is acceptable here because FastAPI runs sync
            # route handlers in a thread pool, so this blocks only the
            # current thread — not the async event loop.
            time.sleep(delay)
        try:
            with request_guard() if request_guard else nullcontext():
                resp = client.request(method, url, params=params, headers=h)
            if 200 <= resp.status_code < 300:
                return resp.json()
            # Retry 429/5xx
            if resp.status_code in (429, 503, 502, 504) and attempt < max_attempts:
                last_exc = ExternalApiError(service, resp.status_code, str(resp.url), resp.text)
                continue
            raise ExternalApiError(service, resp.status_code, str(resp.url), resp.text)
        except (httpx.ConnectError, httpx.ReadTimeout) as exc:  # transient network
            last_exc = exc
            if attempt >= max_attempts:
                raise
            continue
    if last_exc:
        raise last_exc
    raise RuntimeError(f"{service} request failed unexpectedly: {url}")
