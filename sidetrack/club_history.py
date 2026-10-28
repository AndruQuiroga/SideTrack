"""Operator entrypoint for historical club imports; preview requires no DB or provider token."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from sidetrack.club.history import (
    HistoryError,
    apply_checked,
    check_plan,
    load_bundle,
    preview,
    read_object,
    verify_checked,
    write_preview,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sidetrack.club_history")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("preview", help="Prepare an offline, private review plan.")
    prepare.add_argument("--manifest", type=Path, required=True)
    prepare.add_argument("--guild", required=True)
    prepare.add_argument("--source", action="append", required=True, metavar="CHANNEL=ROLE")
    prepare.add_argument("--review", type=Path)
    prepare.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("check", help="Read-only reconciliation against the configured DB.")
    check.add_argument("--plan", type=Path, required=True)
    check.add_argument("--output", type=Path, required=True)
    apply = commands.add_parser("apply", help="Atomically apply an exact checked digest.")
    apply.add_argument("--checked", type=Path, required=True)
    apply.add_argument("--expected-digest", required=True)
    apply.add_argument("--manifest", type=Path, required=True)
    apply.add_argument("--guild", required=True)
    apply.add_argument("--source", action="append", required=True, metavar="CHANNEL=ROLE")
    apply.add_argument("--review", type=Path)
    verify = commands.add_parser("verify", help="Read-only verification of applied targets.")
    verify.add_argument("--checked", type=Path, required=True)
    verify.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            return _check(args.plan, args.output)
        if args.command == "verify":
            return _verify(args.checked, args.output)
        plan = _parse_sources(args)
        if args.command == "apply":
            checked = read_object(args.checked)
            result = _database_operation(
                lambda db: _apply(db, checked, args.expected_digest, plan), write=True
            )
            print(f"Applied batch {result['batch_id']}; digest {checked['digest']}")
            return 0
        write_preview(plan, args.output)
    except (HistoryError, OSError) as exc:
        # OS errors can include private absolute paths; keep those out of routine logs.
        print(
            str(exc) if isinstance(exc, HistoryError) else "Cannot write private preview files.",
            file=sys.stderr,
        )
        return 1
    print(
        f"Preview: {len(plan['messages'])} messages; {len(plan['records'])} candidates; "
        f"{len(plan['issues'])} unresolved issues; digest {plan['digest']}"
    )
    return 0


def _parse_sources(args):
    roles = {}
    for source in args.source:
        pair = source.split("=", 1)
        if len(pair) != 2 or pair[0] in roles:
            raise HistoryError("Assign each source once using CHANNEL=album|singles|supporting.")
        roles[pair[0]] = pair[1]
    bundle = load_bundle(args.manifest, guild_id=args.guild, channels=set(roles))
    return preview(bundle, roles, read_object(args.review) if args.review else None)


def _database_operation(operation, *, write=False):
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import Session

    from sidetrack.config import get_settings
    from sidetrack.db import get_engine, init_engine

    try:
        init_engine(get_settings().database_url)
        with Session(get_engine()) as db, db.begin():
            isolation = "SERIALIZABLE" if write else "REPEATABLE READ, READ ONLY"
            db.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation}"))
            db.execute(text("SET LOCAL lock_timeout = '10s'"))
            return operation(db)
    except HistoryError:
        raise
    except SQLAlchemyError as exc:
        raise HistoryError("Database operation failed; this transaction was not applied.") from exc
    except ValueError as exc:
        raise HistoryError("Database configuration or reviewed fields are invalid.") from exc


def _check(path: Path, output: Path) -> int:
    plan = read_object(path)
    checked = _database_operation(lambda db: check_plan(db, plan))
    # The checked plan contains private attribution decisions. Never send it to public logs.
    output.mkdir(parents=True, exist_ok=False)
    (output / "checked.json").write_text(
        json.dumps(checked, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    counts = Counter(row["action"] for row in checked["records"])
    print(
        f"Check: {dict(sorted(counts.items()))}; {len(checked['conflicts'])} conflicts; "
        f"digest {checked['digest']}"
    )
    return 1 if checked["conflicts"] else 0


def _apply(db, checked, expected, plan):
    batch = apply_checked(db, checked, expected_digest=expected, source_plan=plan)
    return {"batch_id": str(batch.id)}


def _verify(path: Path, output: Path) -> int:
    checked = read_object(path)
    result = _database_operation(lambda db: verify_checked(db, checked))
    output.mkdir(parents=True, exist_ok=False)
    (output / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Verify: {len(result['mismatches'])} mismatches; batch {result['batch_id']}")
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
