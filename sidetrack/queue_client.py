"""Transactional submission over the caller's existing SQLAlchemy connection."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import procrastinate
from procrastinate.jobs import Job
from sqlalchemy import text
from sqlalchemy.orm import Session

from sidetrack.queue_models import BackgroundJob


def enqueue(
    db: Session,
    task: str,
    arguments: dict,
    *,
    queue: str = "default",
    schedule_at: datetime | None = None,
    requested_by: UUID | None = None,
) -> BackgroundJob:
    """Insert both records without committing, opening a pool or closing the session.

    ``requested_by`` is the user who may poll the job's status.
    """
    if queue not in {"default", "musicbrainz", "gpu"}:
        raise ValueError("Unknown queue")
    public_id = uuid4()
    app = procrastinate.App(connector=procrastinate.SyncPsycopgConnector())
    connection = db.connection()
    previous_path = connection.scalar(text("SELECT current_setting('search_path')"))
    connection.execute(text("SET LOCAL search_path TO job_queue, public"))
    # External-connection deferral does not need an open connector/pool.
    deferred = app.job_manager.defer_job(
        Job(
            id=None,
            task_name="sidetrack.execute",
            task_kwargs={"job_id": str(public_id), "task": task, "arguments": arguments},
            queue=queue,
            lock="musicbrainz" if queue == "musicbrainz" else None,
            queueing_lock=None,
            scheduled_at=schedule_at,
        ),
        connection=connection.connection.driver_connection,
    )
    connection.execute(
        text("SELECT set_config('search_path', :path, true)"), {"path": previous_path}
    )
    row = BackgroundJob(
        id=public_id,
        queue_job_id=deferred.id,
        task=task,
        status="deferred" if schedule_at else "queued",
        requested_by_user_id=requested_by,
    )
    db.add(row)
    db.flush()
    return row
