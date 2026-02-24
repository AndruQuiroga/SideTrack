"""RQ worker entrypoint.

Run with:
    python -m services.api.rq_worker

This starts an RQ worker that processes jobs enqueued by the API.
It shares the same codebase and DB connection setup as the API,
but does NOT run migrations or start uvicorn.
"""

from __future__ import annotations

import logging
import sys

from rq import Worker

from services.api.config import get_settings
from services.api.db import init_engine
from services.api.queue import get_queue, get_redis_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("rq-worker")


def main() -> None:
    settings = get_settings()

    # Initialise the DB engine so job functions can use get_db()
    init_engine(settings.database_url)

    conn = get_redis_connection()
    queues = [get_queue("default")]

    logger.info("Starting RQ worker — queues: %s", [q.name for q in queues])
    worker = Worker(queues, connection=conn)
    worker.work()


if __name__ == "__main__":
    main()
