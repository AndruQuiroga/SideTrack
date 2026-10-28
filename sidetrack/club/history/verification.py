"""Read-only verification; never repair or recreate an imported record."""

from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..history_models import HistoryBatch
from .check import check_plan, validate_checked
from .sources import HistoryError


def verify_checked(db: Session, checked: dict[str, Any]) -> dict[str, Any]:
    validate_checked(checked)
    batch = db.scalar(select(HistoryBatch).where(HistoryBatch.plan_digest == checked["digest"]))
    if batch is None:
        raise HistoryError("No applied batch matches the checked plan.")
    current = check_plan(db, checked["preview"])
    mismatches = list(current["conflicts"])
    for row in current["records"]:
        if row["action"] not in {"reuse", "erased"}:
            mismatches.append({"source": row["key"], "reason": "Stored source target is missing."})
    return {
        "batch_id": str(batch.id),
        "plan_digest": checked["digest"],
        "counts": dict(sorted(Counter(row["action"] for row in current["records"]).items())),
        "mismatches": mismatches,
        "verified": not mismatches,
    }
