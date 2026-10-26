"""Use independent real connections to prove transaction ownership."""

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from sidetrack.identity import User
from sidetrack.queue_client import enqueue
from sidetrack.queue_models import BackgroundJob


def test_commit_visibility_and_borrowed_connection(engine):
    with Session(engine) as writer, Session(engine) as observer:
        before = writer.scalar(text("SHOW search_path"))
        user = User(display_name="Atomic queue")
        writer.add(user)
        writer.flush()
        row = enqueue(writer, "unavailable", {})
        job_id, user_id = row.id, user.id
        assert writer.scalar(text("SHOW search_path")) == before
        assert observer.get(BackgroundJob, job_id) is None
        assert observer.get(User, user_id) is None
        writer.commit()
        observer.rollback()
        assert observer.get(BackgroundJob, job_id).queue_job_id == row.queue_job_id
        assert observer.get(User, user_id) is not None
        assert writer.scalar(text("SELECT 1")) == 1
        # Library delete triggers resolve their functions using this path.
        writer.execute(text("SET LOCAL search_path TO job_queue, public"))
        writer.execute(
            text("DELETE FROM procrastinate_jobs WHERE id=:id"), {"id": row.queue_job_id}
        )
        writer.delete(row)
        writer.delete(user)
        writer.commit()


def test_rollback_removes_domain_and_queue_records(engine):
    with Session(engine) as writer, Session(engine) as observer:
        before = observer.scalar(text("SELECT count(*) FROM job_queue.procrastinate_jobs"))
        user = User(display_name="Rolled back")
        writer.add(user)
        writer.flush()
        row = enqueue(writer, "unavailable", {})
        public_id, user_id = row.id, user.id
        writer.rollback()
        assert observer.get(BackgroundJob, public_id) is None
        assert observer.get(User, user_id) is None
        assert observer.scalar(select(func.count()).select_from(BackgroundJob)) == 0
        assert observer.scalar(text("SELECT count(*) FROM job_queue.procrastinate_jobs")) == before
        assert writer.scalar(text("SELECT 1")) == 1
