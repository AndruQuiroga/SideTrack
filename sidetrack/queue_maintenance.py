"""Durable schedule reconciliation, bounded stalled recovery and retention."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from sidetrack.db import database_now
from sidetrack.queue_client import enqueue
from sidetrack.queue_models import BackgroundJob, JobSchedule, ScheduleOccurrence


def reconcile_schedules(db: Session) -> int:
    now = database_now(db)
    schedules = db.scalars(
        select(JobSchedule).where(JobSchedule.next_due_at <= now).with_for_update(skip_locked=True)
    ).all()
    for schedule in schedules:
        due = schedule.next_due_at
        assert due is not None
        db.add(ScheduleOccurrence(schedule_id=schedule.id, revision=schedule.revision, due_at=due))
        enqueue(db, schedule.task, schedule.arguments, queue=schedule.queue)
        if schedule.interval_seconds:
            steps = int((now - due).total_seconds() // schedule.interval_seconds) + 1
            schedule.next_due_at = due + timedelta(seconds=steps * schedule.interval_seconds)
        else:
            schedule.next_due_at = None
    db.flush()
    return len(schedules)


def recover_stalled(db: Session, seconds: float = 30) -> int:
    db.execute(text("SET LOCAL search_path TO job_queue,public"))
    rows = db.execute(
        text(
            "SELECT j.id FROM procrastinate_jobs j LEFT JOIN procrastinate_workers w "
            "ON w.id=j.worker_id WHERE j.status='doing' AND "
            "(w.id IS NULL OR w.last_heartbeat < clock_timestamp()-:seconds*interval '1 second') "
            "FOR UPDATE OF j SKIP LOCKED"
        ),
        {"seconds": seconds},
    ).all()
    count = 0
    for (queue_id,) in rows:
        row = db.scalar(
            select(BackgroundJob)
            .where(BackgroundJob.queue_job_id == queue_id)
            .with_for_update(skip_locked=True)
        )
        if row is None:
            continue
        if row.status == "finished":
            db.execute(
                text("UPDATE procrastinate_jobs SET status='succeeded' WHERE id=:id"),
                {"id": queue_id},
            )
        elif row.attempts >= 3:
            row.status, row.error = "failed", "attempts_exhausted"
            row.finished_at = database_now(db)
            db.execute(
                text("UPDATE procrastinate_jobs SET status='failed' WHERE id=:id"), {"id": queue_id}
            )
        else:
            db.execute(
                text("SELECT procrastinate_retry_job_v2(:id, clock_timestamp(), NULL, NULL, NULL)"),
                {"id": queue_id},
            )
            row.status, row.error = "deferred", "worker_interrupted"
        count += 1
    return count


def cleanup_jobs(db: Session) -> dict:
    cutoff = database_now(db) - timedelta(days=30)
    stale = db.scalars(select(BackgroundJob).where(BackgroundJob.finished_at < cutoff)).all()
    db.execute(text("SET LOCAL search_path TO job_queue,public"))
    deleted = 0
    for row in stale:
        queue_state = db.scalar(
            text("SELECT status::text FROM procrastinate_jobs WHERE id=:id"),
            {"id": row.queue_job_id},
        )
        if queue_state in {"todo", "doing"}:
            continue
        # Preserve nonterminal queue state even if a result was committed before ack.
        db.execute(
            text(
                "DELETE FROM procrastinate_jobs WHERE id=:id AND "
                "status IN ('succeeded','failed','cancelled','aborted')"
            ),
            {"id": row.queue_job_id},
        )
        db.delete(row)
        deleted += 1
    return {"deleted": deleted}


def seed_cleanup(db: Session) -> None:
    from sqlalchemy.dialects.postgresql import insert

    db.execute(
        insert(JobSchedule)
        .values(
            id="system:cleanup",
            revision=1,
            task="system.cleanup",
            arguments={},
            queue="default",
            next_due_at=func.clock_timestamp() + text("interval '1 day'"),
            interval_seconds=86400,
        )
        .on_conflict_do_nothing()
    )
