"""HTTP helpers with retries and User-Agent for external APIs."""

from __future__ import annotations

import time
from typing import Any, Mapping

import httpx


class ExternalApiError(RuntimeError):
    def __init__(self, service: str, status: int, url: str, body: Any | None = None):
        super().__init__(f"{service} returned HTTP {status} for {url}")
        self.service = service
        self.status = status
        self.url = url
        self.body = body


def _retry_delays(max_attempts: int) -> list[float]:
    return [0.0] + [min(2 ** i * 0.25, 3.0) for i in range(1, max_attempts)]


def request_json(
    service: str,
    method: str,
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = 15.0,
    max_attempts: int = 3,
) -> Any:
    h = dict(headers or {})
    # httpx will set a default UA; callers should set a descriptive one
    delays = _retry_delays(max_attempts)
    last_exc: Exception | None = None
    for attempt, delay in enumerate(delays, start=1):
        if delay:
            time.sleep(delay)
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.request(method, url, params=params, headers=h)
                if resp.status_code >= 200 and resp.status_code < 300:
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
