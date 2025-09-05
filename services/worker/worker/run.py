"""Entry point for the RQ worker."""

from __future__ import annotations

import redis
from rq import Connection, Queue, Worker

# Import job functions so the worker process knows about them.
from . import jobs  # noqa: F401
from .config import get_settings


def main() -> None:
    """Start an RQ worker listening to analysis queues."""
    settings = get_settings()
    connection = redis.from_url(settings.redis_url)

    queues = ["analysis"]
    with Connection(connection):
        worker = Worker([Queue(name) for name in queues])
        worker.work()


if __name__ == "__main__":
    main()
