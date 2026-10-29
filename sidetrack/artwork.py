"""Private operator CLI for bounded, reviewed artwork recovery."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from sidetrack import models  # noqa: F401 -- initialize every canonical mapper for operator CLI
from sidetrack.artwork_recovery import apply, check, inventory, preview, reverse, verify
from sidetrack.config import get_settings
from sidetrack.external.artwork import ArtworkError, Discovery


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        path.chmod(0o600)
        json.dump(value, output, indent=2, ensure_ascii=False)
        output.write("\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sidetrack.artwork")
    commands = parser.add_subparsers(dest="command", required=True)
    inv = commands.add_parser("inventory")
    inv.add_argument("--output", type=Path, required=True)
    prep = commands.add_parser("preview")
    prep.add_argument("--inventory", type=Path, required=True)
    prep.add_argument("--review", type=Path)
    prep.add_argument("--output", type=Path, required=True)
    for name in ("check", "apply", "verify", "reverse"):
        p = commands.add_parser(name)
        p.add_argument("--plan", type=Path, required=True)
        if name in {"apply", "reverse"}:
            p.add_argument("--expected-digest", required=True)
        else:
            p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result: Any
    try:
        if args.command == "preview":
            discovery = Discovery()
            try:
                result = preview(
                    read(args.inventory), discovery, read(args.review) if args.review else None
                )
            finally:
                discovery.close()
            write(args.output, result)
            print(
                json.dumps(
                    {
                        "digest": result["digest"],
                        "counts": dict(Counter(e["status"] for e in result["entries"])),
                    }
                )
            )
            return 0
        engine = create_engine(str(get_settings().database_url), isolation_level="SERIALIZABLE")
        try:
            with Session(engine) as db, db.begin():
                if args.command in {"inventory", "check", "verify"}:
                    from sqlalchemy import text

                    db.execute(text("SET TRANSACTION READ ONLY"))
                if args.command == "inventory":
                    result = inventory(db)
                elif args.command == "check":
                    result = check(db, read(args.plan))
                elif args.command == "verify":
                    result = verify(db, read(args.plan))
                elif args.command == "apply":
                    result = {
                        "digest": apply(db, read(args.plan), args.expected_digest).plan_digest
                    }
                else:
                    reverse(db, read(args.plan), args.expected_digest)
                    result = {"reversed": args.expected_digest}
            if hasattr(args, "output"):
                write(args.output, result)
            print(
                json.dumps(
                    {
                        "command": args.command,
                        "ok": result.get("verified", True) if isinstance(result, dict) else True,
                    }
                )
            )
            return 1 if isinstance(result, dict) and result.get("verified") is False else 0
        finally:
            engine.dispose()
    except (ArtworkError, OSError, ValueError, KeyError, TypeError, SQLAlchemyError):
        print(
            "Artwork operation failed; inspect the private plan and target preconditions.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
