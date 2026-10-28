"""Atomic operator application of a checked plan; the caller owns the transaction."""

from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from sidetrack.catalog import ensure_historical_album
from sidetrack.identity import ensure_historical_identity

from ..history_models import HistoryBatch, HistorySource
from ..models import Week
from .check import check_plan, ordered_records, validate_checked
from .fields import reviewed_fields
from .materialize import target_fields
from .report import validate_plan
from .sources import HistoryError
from .store import TARGETS, target_hash


def apply_checked(
    db: Session, checked: dict[str, Any], *, expected_digest: str, source_plan: dict[str, Any]
) -> HistoryBatch:
    """Require a freshly parsed source plan; flush without committing or sending anything.

    The operator entrypoint opens a SERIALIZABLE transaction. Existing target rows
    are also locked before reconciliation. The savepoint prevents partial writes if
    a caller catches a failure inside its outer transaction.
    """
    validate_checked(checked)
    validate_plan(source_plan)
    if checked["digest"] != expected_digest:
        raise HistoryError("Expected checked-plan digest does not match.")
    if checked["preview"] != source_plan:
        raise HistoryError("Fresh source parsing differs from the checked plan.")
    if checked["conflicts"]:
        raise HistoryError("Unresolved checked-plan conflicts prevent application.")
    if db.new or db.dirty or db.deleted:
        raise HistoryError("Application requires a clean session.")
    guild = source_plan["guild_id"]
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"sidetrack:history:{guild}"},
    )
    for item in sorted(checked["records"], key=lambda r: (r["kind"], r["target_id"] or "")):
        if item["target_id"] and item["action"] != "erased":
            model = TARGETS[item["kind"]]
            db.execute(select(model).where(model.id == UUID(item["target_id"])).with_for_update())
    db.expire_all()
    current = check_plan(db, source_plan)
    previous = db.scalar(select(HistoryBatch).where(HistoryBatch.plan_digest == expected_digest))
    if previous is not None:
        # A retry is a read-only verification, including erased-target suppression.
        if current["conflicts"] or any(
            r["action"] not in {"reuse", "erased"} for r in current["records"]
        ):
            raise HistoryError("Previously applied batch no longer matches its stored targets.")
        return previous
    if current["digest"] != expected_digest:
        raise HistoryError("Database changed after check; prepare and review a new check.")
    with db.begin_nested():
        return _write(db, checked)


def _write(db: Session, checked: dict[str, Any]) -> HistoryBatch:
    plan = checked["preview"]
    users: dict[str, str] = {}
    albums: dict[str, str] = {}
    targets: dict[str, str] = {}
    winners: dict[str, str] = {}
    for discord, decision in checked["identities"].items():
        user = ensure_historical_identity(
            db,
            discord_id=discord,
            display_name=decision.get("display_name"),
            handle=decision.get("handle"),
            allow_create=decision["action"] == "create",
        )
        users[discord] = str(user.id)
    for key, decision in checked["albums"].items():
        album = ensure_historical_album(db, **decision["fields"])
        albums[key] = str(album.id)
    batch = HistoryBatch(
        guild_id=plan["guild_id"],
        plan_digest=checked["digest"],
        source_digest=plan["source_digest"],
        parser_version=plan["version"],
        counts=dict(Counter(row["action"] for row in checked["records"])),
    )
    db.add(batch)
    db.flush()
    actions = {row["key"]: row for row in checked["records"]}
    written = []
    changed_weeks = set()
    for record in ordered_records(plan):
        row: Any
        state = actions[record["key"]]
        if state["action"] == "erased":
            continue
        fields = reviewed_fields(record)
        kind = record["kind"]
        if state["action"] in {"reuse", "extend"}:
            row = db.get(TARGETS[kind], UUID(state["target_id"]))
            if row is None:
                raise HistoryError("Checked target disappeared before application.")
            if state["action"] == "extend":
                for name, value in fields.items():
                    if name.endswith("_thread_id") and getattr(row, name) is None:
                        setattr(row, name, value)
                changed_weeks.add(row.id)
        else:
            values = target_fields(
                record,
                fields,
                guild=plan["guild_id"],
                targets=targets,
                users=users,
                albums=albums,
                winners=winners,
            )
            if kind == "winner":
                row = db.get(Week, UUID(targets[fields["week"]]))
                if row is None:
                    raise HistoryError("Checked parent week disappeared before application.")
                for name, value in values.items():
                    setattr(row, name, value)
                changed_weeks.add(row.id)
            else:
                row = TARGETS[kind](**values)
                db.add(row)
            db.flush()
            written.append((record, row))
        targets[record["key"]] = str(row.id)
        if kind == "winner":
            winners[fields["week"]] = str(row.winner_album_id)
    db.flush()
    # One Week is shared by its week and winner source markers. Refresh both only
    # after preflight verified them and this approved operation updated the target.
    if changed_weeks:
        markers = db.scalars(
            select(HistorySource).where(
                HistorySource.target_kind.in_(["week", "winner"]),
                HistorySource.target_id.in_(changed_weeks),
            )
        ).all()
        for marker in markers:
            marker.target_hash = target_hash(db.get(Week, marker.target_id))
    for record, row in written:
        correction = record.get("corrections") or record["fields"].get("correction")
        db.add(
            HistorySource(
                source_key=record["key"],
                batch_id=batch.id,
                kind=record["kind"],
                thread_id=record["thread_id"],
                message_id=record["message_id"],
                evidence_hash=record["evidence_hash"],
                target_kind=record["kind"],
                target_id=row.id,
                target_hash=target_hash(row),
                corrections=correction or None,
            )
        )
    db.flush()
    return batch
