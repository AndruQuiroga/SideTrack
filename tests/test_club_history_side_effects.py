"""The whole operator flow creates no live delivery, queue or acquisition work."""

import subprocess

import httpx
from history_support import sample_plan
from sqlalchemy import func, select, text

from sidetrack.club import ClubMember, Notification
from sidetrack.club.history.application import apply_checked
from sidetrack.club.history.check import check_plan
from sidetrack.club.history.verification import verify_checked
from sidetrack.queue_models import BackgroundJob, JobSchedule, ScheduleOccurrence


def test_apply_verify_retry_have_no_live_side_effects(db, monkeypatch):
    import sidetrack.queue_client

    def forbidden(*args, **kwargs):
        raise AssertionError("Import must not contact providers or enqueue work")

    monkeypatch.setattr(sidetrack.queue_client, "enqueue", forbidden)
    monkeypatch.setattr(httpx.Client, "send", forbidden)
    monkeypatch.setattr(httpx.AsyncClient, "send", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)

    def live_counts():
        values = {
            model.__tablename__: db.scalar(select(func.count()).select_from(model))
            for model in (BackgroundJob, JobSchedule, ScheduleOccurrence, Notification, ClubMember)
        }
        values["actual_queue"] = db.scalar(
            text("SELECT count(*) FROM job_queue.procrastinate_jobs")
        )
        return values

    before = live_counts()
    plan = sample_plan()
    checked = check_plan(db, plan)
    apply_checked(db, checked, expected_digest=checked["digest"], source_plan=plan)
    assert verify_checked(db, checked)["verified"]
    apply_checked(db, checked, expected_digest=checked["digest"], source_plan=plan)
    assert live_counts() == before
