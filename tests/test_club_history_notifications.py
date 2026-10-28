"""Historical dates never become live reminders, even after edits or restarts."""

from datetime import timedelta

from sqlalchemy import func, select

from sidetrack.club import (
    Notification,
    Week,
    claim_notifications,
    produce_notification,
    reconcile_week,
)
from sidetrack.queue_maintenance import reconcile_schedules
from sidetrack.queue_models import JobSchedule


def test_historical_week_retains_dates_but_never_gets_schedules(db):
    now = db.scalar(select(func.clock_timestamp()))
    week = Week(label="Imported", historical=True, nominations_close_at=now - timedelta(days=1))
    db.add(week)
    reconcile_week(db, week)
    assert week.nominations_close_at is not None
    assert db.scalars(select(JobSchedule)).all() == []
    week.nominations_close_at = now + timedelta(days=1)
    reconcile_week(db, week)
    assert db.scalars(select(JobSchedule)).all() == []
    assert reconcile_schedules(db) == 0


def stale_notification(db):
    now = db.scalar(select(func.clock_timestamp()))
    week = Week(
        label="Old live week",
        nominations_thread_id="123",
        nominations_close_at=now - timedelta(seconds=5),
    )
    db.add(week)
    reconcile_week(db, week)
    schedule = db.get(JobSchedule, f"club:{week.id}:nominations-close")
    arguments = schedule.arguments.copy()
    produce_notification(db, **arguments)
    week.historical = True
    db.flush()
    return week, arguments


def test_producer_and_reconcile_disable_stale_pending_delivery(db):
    week, arguments = stale_notification(db)
    assert produce_notification(db, **arguments) == {"skipped": "historical_week"}
    assert db.scalar(select(Notification)).state == "skipped"
    assert all(s.next_due_at is None for s in db.scalars(select(JobSchedule)))
    reconcile_week(db, week)
    assert claim_notifications(db) == []


def test_claim_independently_rejects_historical_pending_notice(db):
    _, _ = stale_notification(db)
    assert claim_notifications(db) == []
    row = db.scalar(select(Notification))
    assert row.state == "skipped" and row.error == "historical_week"
    assert row.attempts == 0


def test_worker_restart_reconcile_does_not_enqueue_obsolete_occurrences(db):
    stale_notification(db)
    assert reconcile_schedules(db) == 0
    assert db.scalar(select(Notification)).state == "skipped"
