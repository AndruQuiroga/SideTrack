"""Entry point for the RQ worker."""
from __future__ import annotations

import os
import redis
from rq import Connection, Queue, Worker

# Import job functions so the worker process knows about them.
from . import jobs  # noqa: F401


def main() -> None:
    """Start an RQ worker listening to analysis queues."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    connection = redis.from_url(redis_url)

    queues = ["analysis"]
    with Connection(connection):
        worker = Worker([Queue(name) for name in queues])
        worker.work()


if __name__ == "__main__":
    main()
