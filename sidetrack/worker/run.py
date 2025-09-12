"""Entry point for the RQ worker."""

from __future__ import annotations

import logging
import threading
import time

import redis
from rq import Connection, Queue, Worker

# Import job functions so the worker process knows about them.
from . import jobs  # noqa: F401
from .config import get_settings


def main() -> None:
    """Start an RQ worker listening to analysis queues."""
    settings = get_settings()
    connection = redis.from_url(settings.redis_url)
    logger = logging.getLogger("sidetrack.worker")

    queues = ["analysis"]
    with Connection(connection):
        worker = Worker([Queue(name) for name in queues])

        def _heartbeat() -> None:
            q = Queue("analysis", connection=connection)
            while True:
                logger.info("worker heartbeat - queue_depth=%s", q.count)
                time.sleep(30)

        threading.Thread(target=_heartbeat, daemon=True).start()
        worker.work()


if __name__ == "__main__":
    main()
