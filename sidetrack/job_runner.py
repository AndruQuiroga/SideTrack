"""Isolated, time-bounded domain execution used by the queue worker."""

from __future__ import annotations

import os
import sys
import threading
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from sidetrack.analysis import compute_user_taste_profile
from sidetrack.club import cleanup_notifications, produce_notification
from sidetrack.config import get_settings
from sidetrack.db import database_now, get_engine, init_engine
from sidetrack.listening import ingest_lastfm
from sidetrack.queue_maintenance import cleanup_jobs
from sidetrack.queue_models import BackgroundJob


def run(job_id: UUID) -> int:
    """Return only safe exit codes; raw errors never cross the process boundary."""
    with Session(get_engine()) as db:
        row = db.scalar(select(BackgroundJob).where(BackgroundJob.id == job_id).with_for_update())
        if row is None:
            return 2
        if row.status == "finished":
            return 0
        payload = db.scalar(
            text("SELECT args FROM job_queue.procrastinate_jobs WHERE id=:id"),
            {"id": row.queue_job_id},
        )
        arguments = payload["arguments"]
        try:
            if row.task == "listening.ingest_lastfm":
                result = ingest_lastfm(
                    db,
                    user_id=UUID(arguments["user_id"]),
                    lastfm_username=arguments["lastfm_username"],
                    since_ts=arguments.get("since_ts"),
                    commit=False,
                )
            elif row.task == "analysis.recompute_taste_profile":
                profile = compute_user_taste_profile(
                    db,
                    user_id=UUID(arguments["user_id"]),
                    scope=arguments.get("scope", "all_time"),
                    commit=False,
                )
                result = {
                    "user_id": str(profile.user_id),
                    "scope": profile.scope,
                    "profile_id": str(profile.user_id),
                }
            elif row.task == "system.cleanup":
                result = cleanup_jobs(db)
                cleanup_notifications(db)
            elif row.task == "club.notify":
                result = produce_notification(db, **arguments)
            else:
                raise NotImplementedError
            row.result = result
            row.status = "finished"
            row.error = None
            row.finished_at = database_now(db)
            db.commit()
            return 0
        except (NotImplementedError, ValueError, KeyError):
            db.rollback()
            return 2
        except Exception:
            db.rollback()
            return 1


def main():
    # Keep execution bounded even if the supervising worker itself is killed.
    timer = threading.Timer(int(sys.argv[2]) if len(sys.argv) > 2 else 600, lambda: os._exit(1))
    timer.daemon = True
    timer.start()
    init_engine(get_settings().database_url)
    raise SystemExit(run(UUID(sys.argv[1])))


if __name__ == "__main__":
    main()
