"""Durable schedule occurrences coalesce downtime and survive transactions."""

from datetime import timedelta

from sqlalchemy import func, select

from sidetrack.queue_maintenance import reconcile_schedules
from sidetrack.queue_models import BackgroundJob, JobSchedule, ScheduleOccurrence


def test_schedule_coalesces_and_does_not_replay(db):
    now = db.scalar(select(func.clock_timestamp()))
    schedule = JobSchedule(
        id="test:recurring",
        revision=1,
        task="system.cleanup",
        arguments={},
        queue="default",
        next_due_at=now - timedelta(hours=2),
        interval_seconds=60,
    )
    db.add(schedule)
    db.flush()
    assert reconcile_schedules(db) == 1
    assert schedule.next_due_at > now
    assert reconcile_schedules(db) == 0
    assert db.scalar(select(func.count()).select_from(BackgroundJob)) == 1
    assert db.scalar(select(func.count()).select_from(ScheduleOccurrence)) == 1


def test_one_shot_rollback_and_restart(db):
    now = db.scalar(select(func.clock_timestamp()))
    schedule = JobSchedule(
        id="test:once",
        revision=1,
        task="system.cleanup",
        arguments={},
        queue="default",
        next_due_at=now - timedelta(seconds=1),
    )
    db.add(schedule)
    db.flush()
    with db.begin_nested() as transaction:
        assert reconcile_schedules(db) == 1
        transaction.rollback()
    db.expire_all()
    assert reconcile_schedules(db) == 1
    assert schedule.next_due_at is None
    db.expire_all()
    assert reconcile_schedules(db) == 0


def test_competing_schedulers_create_one_occurrence(engine):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from uuid import uuid4

    from sqlalchemy import delete, text
    from sqlalchemy.orm import Session

    key = f"test:{uuid4()}"
    barrier = Barrier(2)
    with Session(engine) as db, db.begin():
        db.add(
            JobSchedule(
                id=key,
                revision=1,
                task="system.cleanup",
                arguments={"test": key},
                queue="default",
                next_due_at=db.scalar(select(func.clock_timestamp())),
            )
        )

    def reconcile(_):
        with Session(engine) as db, db.begin():
            barrier.wait(timeout=5)
            return reconcile_schedules(db)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(reconcile, range(2))) == [0, 1]
        with Session(engine) as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(ScheduleOccurrence)
                    .where(ScheduleOccurrence.schedule_id == key)
                )
                == 1
            )
    finally:
        with engine.begin() as conn:
            conn.execute(text("SET LOCAL search_path TO job_queue,public"))
            queue_ids = conn.scalars(
                text("SELECT id FROM procrastinate_jobs " "WHERE args->'arguments'->>'test'=:key"),
                {"key": key},
            ).all()
            for queue_id in queue_ids:
                conn.execute(delete(BackgroundJob).where(BackgroundJob.queue_job_id == queue_id))
                conn.execute(text("DELETE FROM procrastinate_jobs WHERE id=:id"), {"id": queue_id})
            conn.execute(delete(JobSchedule).where(JobSchedule.id == key))


def test_cleanup_keeps_occurrence_identity_and_active_ack_window(db):
    from sqlalchemy import text

    from sidetrack.queue_maintenance import cleanup_jobs

    now = db.scalar(select(func.clock_timestamp()))
    db.add(
        JobSchedule(
            id="test:retention",
            revision=1,
            task="system.cleanup",
            arguments={},
            queue="default",
            next_due_at=now - timedelta(seconds=1),
        )
    )
    db.flush()
    assert reconcile_schedules(db) == 1
    job = db.scalar(select(BackgroundJob))
    job.status, job.finished_at = "finished", now - timedelta(days=31)
    db.flush()
    assert cleanup_jobs(db) == {"deleted": 0}  # Active queue acknowledgment is still pending.
    db.execute(
        text("UPDATE job_queue.procrastinate_jobs SET status='succeeded' WHERE id=:id"),
        {"id": job.queue_job_id},
    )
    assert cleanup_jobs(db) == {"deleted": 1}
    db.flush()
    assert db.scalar(select(func.count()).select_from(ScheduleOccurrence)) == 1
    assert reconcile_schedules(db) == 0
