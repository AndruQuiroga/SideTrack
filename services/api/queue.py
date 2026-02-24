"""Redis connection and RQ queue factory for background job dispatch."""

from __future__ import annotations

from functools import lru_cache

import redis
from rq import Queue

from services.api.config import get_settings


@lru_cache(maxsize=1)
def get_redis_connection() -> redis.Redis:
    """Return a cached Redis connection based on settings."""
    settings = get_settings()
    return redis.from_url(settings.redis_url)


def get_queue(name: str = "default") -> Queue:
    """Return an RQ queue bound to the shared Redis connection."""
    return Queue(name, connection=get_redis_connection())
