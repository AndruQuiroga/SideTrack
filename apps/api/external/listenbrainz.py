"""ListenBrainz client helpers for Sidetrack MVP (optional)."""

from __future__ import annotations

from typing import Any

from apps.api.config import get_settings
from .http import request_json

BASE_URL = "https://api.listenbrainz.org/1"


def _headers() -> dict[str, str]:
    settings = get_settings()
    ua = settings.listenbrainz_user_agent or settings.app_name
    return {"User-Agent": ua}


def get_listens(user_name: str, *, min_ts: int | None = None, count: int = 100) -> dict[str, Any]:
    params: dict[str, str] = {"count": str(count)}
    if min_ts is not None:
        params["min_ts"] = str(min_ts)
    return request_json("listenbrainz", "GET", f"{BASE_URL}/user/{user_name}/listens", params=params, headers=_headers())


def get_playing_now(user_name: str) -> dict[str, Any]:
    return request_json("listenbrainz", "GET", f"{BASE_URL}/user/{user_name}/playing-now", headers=_headers())
