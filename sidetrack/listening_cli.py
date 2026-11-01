"""Operator command for listening history imports. Nothing else starts them.

    python -m sidetrack.listening backfill --user <uuid> [--until YYYY-MM-DD]
    python -m sidetrack.listening sync --user <uuid>
    python -m sidetrack.listening import-export --user <uuid> --export <dir>
    python -m sidetrack.listening sessionize --user <uuid> [--rebuild]
    python -m sidetrack.listening schedule --user <uuid> [--enable | --disable]

It uses the operator's database access (DATABASE_URL), like Alembic.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sidetrack import models  # noqa: F401  (configures every mapper)
from sidetrack.config import get_settings
from sidetrack.db import get_engine, init_engine
from sidetrack.listening import (
    ImportUnavailable,
    ListenSession,
    import_export,
    linked_account,
    sessionize,
)
from sidetrack.queue_client import enqueue
from sidetrack.queue_models import JobSchedule

TASK = "listening.ingest_listenbrainz"
SYNC_INTERVAL_S = 3600


def queue_import(db: Session, user_id: UUID, *, mode: str, until_ts: int | None = None) -> str:
    """Queue the first page; the caller commits."""

    linked_account(db, user_id)
    arguments: dict[str, Any] = {"user_id": str(user_id), "mode": mode}
    if until_ts is not None:
        arguments["until_ts"] = until_ts
    return str(enqueue(db, TASK, arguments, requested_by=user_id).id)


def schedule_sync(db: Session, user_id: UUID, *, enabled: bool) -> JobSchedule:
    """The hourly sync for an account, disabled until the operator enables it.

    A schedule with no due time is never reconciled. The caller commits.
    """

    linked_account(db, user_id)
    schedule_id = f"listenbrainz-sync:{user_id}"
    schedule = db.get(JobSchedule, schedule_id)
    if schedule is None:
        schedule = JobSchedule(
            id=schedule_id,
            task=TASK,
            arguments={"user_id": str(user_id), "mode": "sync"},
            queue="default",
            interval_seconds=SYNC_INTERVAL_S,
        )
        db.add(schedule)
    schedule.next_due_at = datetime.now(UTC) if enabled else None
    db.flush()
    return schedule


def run_sessionize(db: Session, user_id: UUID, *, rebuild: bool) -> dict[str, Any]:
    since = None
    if not rebuild:
        since = db.scalar(
            select(func.max(ListenSession.ended_at)).where(ListenSession.user_id == user_id)
        )
    return sessionize(db, user_id, since=since)


def _until(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m sidetrack.listening")
    commands = parser.add_subparsers(dest="command", required=True)
    backfill = commands.add_parser("backfill", help="Queue a full history import.")
    backfill.add_argument("--user", type=UUID, required=True)
    backfill.add_argument("--until", type=_until, help="Stop at this UTC date, YYYY-MM-DD.")
    sync = commands.add_parser("sync", help="Queue listens newer than the checkpoint.")
    sync.add_argument("--user", type=UUID, required=True)
    export = commands.add_parser("import-export", help="Import an export directory here.")
    export.add_argument("--user", type=UUID, required=True)
    export.add_argument("--export", type=Path, required=True)
    sessions = commands.add_parser("sessionize", help="Build sessions from stored listens.")
    sessions.add_argument("--user", type=UUID, required=True)
    sessions.add_argument("--rebuild", action="store_true", help="Rebuild every session.")
    schedule = commands.add_parser("schedule", help="Define the hourly sync, disabled by default.")
    schedule.add_argument("--user", type=UUID, required=True)
    schedule.add_argument("--enable", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    init_engine(get_settings().database_url)
    with Session(get_engine()) as db:
        try:
            if args.command == "backfill":
                print(queue_import(db, args.user, mode="backfill", until_ts=args.until))
            elif args.command == "sync":
                print(queue_import(db, args.user, mode="sync"))
            elif args.command == "import-export":
                print(json.dumps(import_export(db, user_id=args.user, root=args.export)))
            elif args.command == "sessionize":
                print(json.dumps(run_sessionize(db, args.user, rebuild=args.rebuild)))
            else:
                schedule = schedule_sync(db, args.user, enabled=args.enable)
                print(f"{schedule.id}: {'enabled' if args.enable else 'disabled'}")
            db.commit()
        except ImportUnavailable as exc:
            print(str(exc), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
