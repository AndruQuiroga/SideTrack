"""Week revisions, restart catch-up and idempotent outbox production."""

from datetime import timedelta

from sqlalchemy import func, select

from sidetrack.club import Notification, Week, produce_notification, reconcile_week
from sidetrack.queue_maintenance import reconcile_schedules
from sidetrack.queue_models import JobSchedule


def scheduled_week(db):
    now = db.scalar(select(func.clock_timestamp()))
    week = Week(
        label="Durable week",
        nominations_thread_id="123",
        nominations_close_at=now - timedelta(minutes=10),
        poll_close_at=now + timedelta(hours=1),
    )
    db.add(week)
    reconcile_week(db, week)
    return week


def test_catchup_idempotence_and_expired_reminder(db):
    week = scheduled_week(db)
    assert reconcile_schedules(db) == 3
    for schedule in db.scalars(select(JobSchedule)).all():
        if schedule.arguments["kind"] != "auto-open-ratings":
            produce_notification(db, **schedule.arguments)
            produce_notification(db, **schedule.arguments)
    events = db.scalars(select(Notification)).all()
    assert len(events) == 3
    assert sorted(e.state for e in events) == ["pending", "pending", "skipped"]
    assert next(e for e in events if e.state == "skipped").error == "reminder_expired"
    # Unrelated edits and restarts cannot recreate already consumed deadlines.
    reconcile_week(db, week)
    assert reconcile_schedules(db) == 0


def test_deadline_edit_invalidates_pending_and_rollback_is_atomic(db):
    week = scheduled_week(db)
    schedule = db.get(JobSchedule, f"club:{week.id}:nominations-close")
    old_args = schedule.arguments.copy()
    produce_notification(db, **old_args)
    with db.begin_nested() as transaction:
        week.nominations_close_at += timedelta(minutes=5)
        reconcile_week(db, week)
        assert schedule.revision == 2
        transaction.rollback()
    db.expire_all()
    assert db.get(JobSchedule, schedule.id).revision == 1
    assert db.scalar(select(Notification)).state == "pending"
    week.nominations_close_at += timedelta(minutes=5)
    reconcile_week(db, week)
    assert db.scalar(select(Notification)).state == "skipped"
    assert produce_notification(db, **old_args) == {"skipped": "obsolete_schedule"}
    week.nominations_close_at = None
    reconcile_week(db, week)
    assert db.get(JobSchedule, schedule.id).next_due_at is None


def test_deleted_week_cascades_outbox_and_suppresses_old_occurrences(db):
    from sqlalchemy import delete

    week = scheduled_week(db)
    arguments = db.get(JobSchedule, f"club:{week.id}:nominations-close").arguments.copy()
    produce_notification(db, **arguments)
    db.execute(delete(Week).where(Week.id == week.id))
    assert db.scalar(select(func.count()).select_from(Notification)) == 0
    assert produce_notification(db, **arguments) == {"skipped": "obsolete_schedule"}
    assert db.scalar(select(func.count()).select_from(Notification)) == 0


def test_competing_producers_create_one_notification(engine):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete
    from sqlalchemy.orm import Session

    with Session(engine) as db, db.begin():
        week = scheduled_week(db)
        week_id = week.id
        arguments = db.get(JobSchedule, f"club:{week.id}:nominations-close").arguments.copy()
    barrier = Barrier(2)

    def produce(_):
        with Session(engine) as db, db.begin():
            barrier.wait(timeout=5)
            produce_notification(db, **arguments)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(produce, range(2)))
        with Session(engine) as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(Notification)
                    .where(Notification.week_id == week_id)
                )
                == 1
            )
    finally:
        with engine.begin() as conn:
            conn.execute(delete(JobSchedule).where(JobSchedule.id.like(f"club:{week_id}:%")))
            conn.execute(delete(Week).where(Week.id == week_id))
