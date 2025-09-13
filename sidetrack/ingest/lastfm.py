"""Last.fm scrobble retrieval and ingestion CLI.

Use this module to fetch a user's Last.fm scrobbles (recent tracks) and ingest
them into the SideTrack database. It relies on the existing SQLAlchemy models
and the ListenService used by the API, so ingested rows appear exactly as if
they were pulled via the API endpoint.

Environment
- DATABASE_URL must point to your Postgres instance
- LASTFM_API_KEY must be set (public reads only; no secret required)

Examples
- python -m sidetrack.ingest.lastfm --user mylastfm --since 2024-01-01
- python -m sidetrack.ingest.lastfm --user mylastfm --as-user some_user
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime
from typing import Any, Iterable, List

import httpx

from sidetrack.api.clients.lastfm import LastfmClient
from sidetrack.api.config import get_settings
from sidetrack.api.db import SessionLocal
from sidetrack.api.services.listen_service import ListenService, get_listen_service


class LastfmIngester:
    """Fetch listens from the Last.fm API and ingest them into the DB."""

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    async def fetch_recent(
        self, user: str, since: datetime | None = None, *, limit: int = 200
    ) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            lf = LastfmClient(client, self.api_key, api_secret=None)
            return await lf.fetch_recent_tracks(user, since=since, limit=limit)

    async def ingest(
        self,
        *,
        lastfm_user: str,
        as_user: str | None = None,
        since: datetime | None = None,
    ) -> int:
        """Fetch recent tracks and ingest as listens for ``as_user``.

        Returns the number of newly created listens.
        """
        # Ensure DB engines are initialized with current env
        async with SessionLocal(async_session=True) as db:
            service: ListenService = get_listen_service(db)  # type: ignore[arg-type]
            tracks = await self.fetch_recent(lastfm_user, since)
            target_user = as_user or lastfm_user
            created = await service.ingest_lastfm_rows(tracks, target_user)
            return created


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch Last.fm scrobbles and ingest into DB")
    p.add_argument("--user", required=True, help="Last.fm username to fetch")
    p.add_argument(
        "--as-user",
        help="User id to attribute listens to in the DB (defaults to --user)",
    )
    p.add_argument(
        "--since",
        help="Earliest date to fetch (YYYY-MM-DD). Defaults to all recent tracks.",
    )
    p.add_argument(
        "--database-url",
        help="Override DATABASE_URL for this run (postgresql+psycopg URL)",
    )
    return p.parse_args(argv)


async def _amain(args: argparse.Namespace) -> int:
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    # Refresh settings cache so DB layer sees changes
    get_settings.cache_clear()

    since_dt: datetime | None = None
    if args.since:
        try:
            since_dt = datetime.fromisoformat(args.since)
        except ValueError:
            raise SystemExit("--since must be in YYYY-MM-DD or ISO format")

    settings = get_settings()
    ingester = LastfmIngester(settings.lastfm_api_key)
    created = await ingester.ingest(lastfm_user=args.user, as_user=args.as_user, since=since_dt)
    print(f"Ingested {created} listens from Last.fm for {args.user} → user={args.as_user or args.user}")
    return 0


def main(argv: Iterable[str] | None = None) -> None:
    args = _parse_args(argv)
    raise SystemExit(asyncio.run(_amain(args)))


if __name__ == "__main__":  # pragma: no cover - manual/CLI usage
    main()
