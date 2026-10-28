"""Club-owned target snapshots and replay markers. These helpers do not commit."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from ..history_models import (
    HistorySource,
    SinglesRating,
    SinglesSession,
    SinglesSong,
    SinglesSubmission,
)
from ..models import Nomination, Rating, Week
from .sources import HistoryError, digest

TARGETS: dict[str, type[Any]] = {
    "week": Week,
    "winner": Week,
    "nomination": Nomination,
    "rating": Rating,
    "singles_session": SinglesSession,
    "singles_song": SinglesSong,
    "singles_submission": SinglesSubmission,
    "singles_rating": SinglesRating,
}


def json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID | Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [json_value(item) for item in value]
    return value


def snapshot(row: Any) -> dict[str, Any]:
    return {
        column.key: json_value(getattr(row, column.key))
        for column in inspect(type(row)).column_attrs
    }


def target_hash(row: Any) -> str:
    return digest(snapshot(row))


def source_state(db: Session, record: dict[str, Any]) -> dict[str, Any]:
    marker = db.get(HistorySource, record["key"])
    if marker is None:
        return {"action": "new", "target_id": None, "target_hash": None}
    if marker.kind != record["kind"] or marker.target_kind != record["kind"]:
        raise HistoryError("Source ledger kind conflicts with the reviewed record.")
    row = db.get(TARGETS[marker.target_kind], marker.target_id)
    if row is None:
        return {"action": "erased", "target_id": str(marker.target_id), "target_hash": None}
    if marker.evidence_hash != record["evidence_hash"]:
        raise HistoryError("Previously imported source evidence has changed.")
    current = target_hash(row)
    if current != marker.target_hash:
        raise HistoryError("Previously imported target has changed.")
    return {"action": "reuse", "target_id": str(marker.target_id), "target_hash": current}
