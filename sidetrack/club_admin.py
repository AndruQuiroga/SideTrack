"""Operator command that grants the club admin role without any API credential.

    python -m sidetrack.club_admin grant-admin --user-id <uuid>
    python -m sidetrack.club_admin grant-admin --discord-id <snowflake>

It uses the operator's database access (DATABASE_URL), like Alembic.
"""

from __future__ import annotations

import argparse
import sys
from uuid import UUID

from sqlalchemy.orm import Session

from sidetrack import models  # noqa: F401  (configures every mapper)
from sidetrack.club import upsert_member
from sidetrack.config import get_settings
from sidetrack.db import get_engine, init_engine
from sidetrack.identity import User, auth
from sidetrack.types import ClubRole


def grant_admin(db: Session, *, user_id: UUID | None = None, discord_id: str | None = None) -> UUID:
    """Make an existing user a club admin; the caller commits."""

    if discord_id is not None:
        user_id = auth.resolve_discord_user(db, discord_id)
        if user_id is None:
            raise LookupError(f"No user has Discord account {discord_id} linked.")
    if user_id is None or db.get(User, user_id) is None:
        raise LookupError(f"No user {user_id}.")
    upsert_member(db, user_id, ClubRole.ADMIN)
    return user_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sidetrack.club_admin")
    commands = parser.add_subparsers(dest="command", required=True)
    grant = commands.add_parser("grant-admin", help="Make an existing user a club admin.")
    who = grant.add_mutually_exclusive_group(required=True)
    who.add_argument("--user-id", type=UUID)
    who.add_argument("--discord-id")
    args = parser.parse_args(argv)

    init_engine(get_settings().database_url)
    with Session(get_engine()) as db:
        try:
            user_id = grant_admin(db, user_id=args.user_id, discord_id=args.discord_id)
        except LookupError as exc:
            print(exc, file=sys.stderr)
            return 1
        db.commit()
    print(f"User {user_id} is now a club admin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
