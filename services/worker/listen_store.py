"""Listen event store — deduplication and direct DB upsert.

This replaces the TS ListenEventStore which went through the API via HTTP.
The Python worker writes directly to PostgreSQL for lower latency and simpler code.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from services.api.models import LinkedAccount, ListenEvent
from services.api.models.listening import ListenSource

from .connectors.base import NormalizedListen

logger = logging.getLogger(__name__)

_UUID_PATTERN_PARTS = (8, 4, 4, 4, 12)


def deterministic_uuid(input_str: str) -> uuid.UUID:
    """Generate a deterministic UUID from an input string via SHA-1.

    Matches the TS worker's `deterministicUuid` for compatibility.
    """
    hex_digest = hashlib.sha1(input_str.encode()).hexdigest()[:32]
    parts: list[str] = []
    offset = 0
    for length in _UUID_PATTERN_PARTS:
        parts.append(hex_digest[offset : offset + length])
        offset += length
    return uuid.UUID("-".join(parts))


class ListenIngestResult:
    """Result of a listen-event upsert batch."""

    __slots__ = ("ingested", "skipped", "last_played_at")

    def __init__(
        self,
        ingested: int = 0,
        skipped: int = 0,
        last_played_at: datetime | None = None,
    ) -> None:
        self.ingested = ingested
        self.skipped = skipped
        self.last_played_at = last_played_at


class ListenEventStore:
    """Deduplicates and upserts listen events directly to the database."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def upsert(
        self,
        db: Session,
        user_id: uuid.UUID,
        source: ListenSource,
        listens: list[NormalizedListen],
        account: LinkedAccount,
    ) -> ListenIngestResult:
        """Deduplicate and insert listen events into the database.

        Uses PostgreSQL ON CONFLICT DO NOTHING for idempotent inserts,
        plus an in-memory cache to avoid redundant DB round-trips.
        """
        rows: list[dict] = []
        for listen in listens:
            track_uuid = deterministic_uuid(f"{source.value}:{listen.track_external_id}")
            played_at_iso = listen.played_at.isoformat()
            key = f"{user_id}:{track_uuid}:{played_at_iso}"

            if key in self._seen:
                continue

            metadata = {**listen.metadata, "provider_user_id": account.provider_user_id}
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "user_id": user_id,
                    "track_id": track_uuid,
                    "played_at": listen.played_at,
                    "source": source,
                    "metadata": metadata,
                }
            )
            self._seen.add(key)

        if not rows:
            return ListenIngestResult(ingested=0, skipped=len(listens))

        # Batch upsert — ON CONFLICT DO NOTHING honours the unique constraint
        stmt = (
            pg_insert(ListenEvent)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_listen_event_dedup")
        )
        result = db.execute(stmt)
        db.commit()

        ingested = result.rowcount if result.rowcount else len(rows)
        last_played = listens[0].played_at if listens else None

        logger.info(
            "Upserted %d listen events for user %s (source=%s, skipped=%d)",
            ingested,
            user_id,
            source.value,
            len(listens) - len(rows),
        )

        return ListenIngestResult(
            ingested=ingested,
            skipped=len(listens) - len(rows),
            last_played_at=last_played,
        )
