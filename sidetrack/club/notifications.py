"""Club-owned schedule production and leased Discord delivery operations."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from sidetrack.db import database_now
from sidetrack.queue_models import JobSchedule

from .models import Notification, Week


def reconcile_week(db: Session, week: Week) -> None:
    db.flush()
    deadlines = {
        "nominations-1h-reminder": week.nominations_close_at - timedelta(hours=1)
        if week.nominations_close_at
        else None,
        "nominations-close": week.nominations_close_at,
        "auto-open-poll": week.nominations_close_at,
        "auto-open-ratings": week.poll_close_at,
    }
    for kind, deadline in deadlines.items():
        key = f"club:{week.id}:{kind}"
        schedule = db.get(JobSchedule, key, with_for_update=True)
        if schedule:
            old = schedule.arguments.get("deadline")
            # Parse timestamps so SQL cutover seed and Python use the same identity.
            if (datetime.fromisoformat(old) if old else None) == deadline:
                continue
            schedule.revision += 1
            db.execute(
                update(Notification)
                .where(Notification.schedule_id == key, Notification.state == "pending")
                .values(state="skipped", error="schedule_replaced")
            )
        else:
            schedule = JobSchedule(id=key, revision=1, task="club.notify", queue="default")
            db.add(schedule)
        schedule.arguments = {
            "week_id": str(week.id),
            "kind": kind,
            "deadline": deadline.isoformat() if deadline else None,
            "revision": schedule.revision,
        }
        schedule.next_due_at = deadline
    db.flush()


def produce_notification(
    db: Session, *, week_id: str, kind: str, revision: int, deadline: str | None
) -> dict:
    week = db.get(Week, UUID(week_id))
    key = f"club:{week_id}:{kind}"
    schedule = db.get(JobSchedule, key, with_for_update=True)
    if week is None or schedule is None or schedule.revision != revision:
        return {"skipped": "obsolete_schedule"}
    now = database_now(db)
    messages = {
        "nominations-1h-reminder": (
            f"⏰ Nominations close in 1 hour for **{week.label}**. Submit your pick!"
        ),
        "nominations-close": f"🔒 Nominations are now closed for **{week.label}**.",
        "auto-open-poll": f"🗳️ Nominations have closed for **{week.label}**. Voting is now open!",
        "auto-open-ratings": (
            f"⭐ Voting has closed for **{week.label}**. Time to listen and rate the winner!"
        ),
    }
    if kind not in messages:
        raise ValueError("unavailable_notification")
    target = (
        week.winner_thread_id or week.nominations_thread_id
        if kind == "auto-open-ratings"
        else week.nominations_thread_id
    )
    expired = kind == "nominations-1h-reminder" and (
        week.nominations_close_at is None or week.nominations_close_at <= now
    )
    reason = "reminder_expired" if expired else "target_unavailable" if not target else None
    db.execute(
        insert(Notification)
        .values(
            id=uuid4(),
            week_id=week.id,
            schedule_id=key,
            revision=revision,
            kind=kind,
            thread_id=target,
            message=messages[kind],
            state="skipped" if reason else "pending",
            attempts=0,
            next_attempt_at=now,
            error=reason,
        )
        .on_conflict_do_nothing(constraint="club_notification_outbox_schedule_id_revision_key")
    )
    return {"skipped": reason} if reason else {"notification": key}


def claim_notifications(db: Session, limit: int = 1) -> list[Notification]:
    now = database_now(db)
    rows = db.scalars(
        select(Notification)
        .join(JobSchedule)
        .where(
            Notification.revision == JobSchedule.revision,
            Notification.next_attempt_at <= now,
            or_(
                Notification.state == "pending",
                (Notification.state == "leased") & (Notification.lease_until <= now),
            ),
        )
        .order_by(Notification.next_attempt_at, Notification.id)
        .with_for_update(of=Notification, skip_locked=True)
        .limit(limit)
    ).all()
    claimed = []
    for row in rows:
        week = db.get(Week, row.week_id)
        if row.kind == "nominations-1h-reminder" and (
            not week or not week.nominations_close_at or week.nominations_close_at <= now
        ):
            row.state, row.error = "skipped", "reminder_expired"
        elif row.attempts >= 3:
            row.state, row.error = "failed", "delivery_exhausted"
        else:
            row.attempts += 1
            row.state, row.token = "leased", uuid4()
            row.lease_until = now + timedelta(seconds=60)
            claimed.append(row)
    db.flush()
    return claimed


def finish_notification(
    db: Session,
    event_id: UUID,
    token: UUID,
    *,
    message_id: str | None = None,
    permanent: bool = False,
    retry_after: int = 0,
) -> bool:
    now = database_now(db)
    row = db.get(Notification, event_id, with_for_update=True)
    if (
        not row
        or row.state != "leased"
        or row.token != token
        or row.lease_until is None
        or row.lease_until <= now
    ):
        return False
    row.token, row.lease_until = None, None
    if message_id:
        row.state, row.message_id, row.delivered_at = "sent", message_id, now
        row.error = None
    elif permanent or row.attempts >= 3:
        row.state, row.error = (
            "failed",
            "delivery_unavailable" if permanent else "delivery_exhausted",
        )
    else:
        row.state, row.error = "pending", "delivery_retry"
        row.next_attempt_at = now + timedelta(seconds=max(2**row.attempts, min(retry_after, 300)))
    db.flush()
    return True


def cleanup_notifications(db: Session) -> None:
    cutoff = database_now(db) - timedelta(days=30)
    db.execute(delete(Notification).where(Notification.delivered_at < cutoff))
