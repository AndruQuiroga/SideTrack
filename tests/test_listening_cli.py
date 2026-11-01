"""The operator command behind `python -m sidetrack.listening`."""

import json
from uuid import UUID, uuid4

import pytest
from listenbrainz_doubles import listen
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from sidetrack import db as database
from sidetrack import listening_cli
from sidetrack.catalog import Track
from sidetrack.identity import LinkedAccount, User
from sidetrack.listening import ListenEvent, ListenSession
from sidetrack.queue_models import BackgroundJob, JobSchedule
from sidetrack.types import ProviderType

pytestmark = pytest.mark.unit


@pytest.fixture
def operator(engine, monkeypatch):
    monkeypatch.setattr(listening_cli, "init_engine", lambda url: None)
    monkeypatch.setattr(database, "_engine", engine)
    with Session(engine) as writer:
        linked = User(display_name="CLI listener", timezone="UTC")
        unlinked = User(display_name="CLI unlinked")
        writer.add_all([linked, unlinked])
        writer.flush()
        writer.add(
            LinkedAccount(
                user_id=linked.id,
                provider=ProviderType.LISTENBRAINZ,
                provider_user_id=f"cli-{uuid4()}",
            )
        )
        ids = linked.id, unlinked.id
        writer.commit()
    yield ids
    with Session(engine) as cleanup:
        jobs = cleanup.execute(
            delete(BackgroundJob)
            .where(BackgroundJob.requested_by_user_id.in_(ids))
            .returning(BackgroundJob.queue_job_id)
        ).scalars()
        cleanup.execute(text("SET LOCAL search_path TO job_queue, public"))
        cleanup.execute(
            text("DELETE FROM job_queue.procrastinate_jobs WHERE id = ANY(:ids)"),
            {"ids": list(jobs)},
        )
        cleanup.execute(delete(JobSchedule).where(JobSchedule.id.like("listenbrainz-sync:%")))
        tracks = cleanup.scalars(
            select(ListenEvent.track_id).where(ListenEvent.user_id.in_(ids))
        ).all()
        cleanup.execute(delete(User).where(User.id.in_(ids)))
        cleanup.execute(delete(Track).where(Track.id.in_(tracks)))
        cleanup.commit()


def _job(engine, job_id):
    with Session(engine) as reader:
        return reader.get(BackgroundJob, UUID(job_id))


def test_backfill_prints_the_queued_job(operator, engine, capsys):
    assert (
        listening_cli.main(["backfill", "--user", str(operator[0]), "--until", "2024-01-01"]) == 0
    )
    job = _job(engine, capsys.readouterr().out.strip())
    assert (job.task, job.status) == ("listening.ingest_listenbrainz", "queued")
    assert job.requested_by_user_id == operator[0]


def test_sync_prints_the_queued_job(operator, engine, capsys):
    assert listening_cli.main(["sync", "--user", str(operator[0])]) == 0
    assert _job(engine, capsys.readouterr().out.strip()).status == "queued"


@pytest.mark.parametrize("command", ["backfill", "sync"])
def test_account_not_linked_queues_nothing(operator, engine, capsys, command):
    with Session(engine) as reader:
        before = reader.scalar(select(func.count()).select_from(BackgroundJob))
    assert listening_cli.main([command, "--user", str(operator[1])]) == 1
    assert "account_not_linked" in capsys.readouterr().err
    with Session(engine) as reader:
        assert reader.scalar(select(func.count()).select_from(BackgroundJob)) == before


def test_export_import_prints_counts_and_session_rebuild(operator, engine, capsys, tmp_path):
    folder = tmp_path / "listens" / "2026"
    folder.mkdir(parents=True)
    records = [listen(100_000), listen(100_300, title="Two"), listen(200_000, title="Three")]
    (folder / "10.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records), encoding="utf-8"
    )
    arguments = ["import-export", "--user", str(operator[0]), "--export", str(tmp_path)]
    assert listening_cli.main(arguments) == 0
    output = capsys.readouterr().out
    assert str(tmp_path) not in output
    assert (json.loads(output)["fetched"], json.loads(output)["stored"]) == (3, 3)

    assert listening_cli.main(["sessionize", "--user", str(operator[0]), "--rebuild"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["sessions"] == 2
    with Session(engine) as reader:
        assert (
            reader.scalar(
                select(func.count())
                .select_from(ListenEvent)
                .where(ListenEvent.user_id == operator[0], ListenEvent.session_id.is_(None))
            )
            == 0
        )
        sessions = select(func.count()).select_from(ListenSession)
        assert reader.scalar(sessions.where(ListenSession.user_id == operator[0])) == 2


def test_schedule_is_disabled_unless_enabled(operator, capsys):
    assert listening_cli.main(["schedule", "--user", str(operator[0])]) == 0
    assert capsys.readouterr().out.strip().endswith(": disabled")
    assert listening_cli.main(["schedule", "--user", str(operator[0]), "--enable"]) == 0
    assert capsys.readouterr().out.strip().endswith(": enabled")


def _timezone(user, *arguments):
    return listening_cli.main(["timezone", "--user", str(user), *arguments])


def test_timezone_add_list_remove(operator, capsys):
    assert _timezone(operator[0]) == 0
    assert capsys.readouterr().out.strip() == ""
    add = ["--add", "--from", "2026-03-01", "--zone", "America/New_York"]
    assert _timezone(operator[0], "--add", "--from", "2026-01-01", "--zone", "America/Phoenix") == 0
    assert _timezone(operator[0], *add) == 0
    capsys.readouterr()
    assert _timezone(operator[0], "--list") == 0
    assert capsys.readouterr().out.splitlines() == [
        "2026-01-01 America/Phoenix",
        "2026-03-01 America/New_York",
    ]
    assert _timezone(operator[0], "--remove", "--from", "2026-01-01") == 0
    capsys.readouterr()
    assert _timezone(operator[0]) == 0
    assert capsys.readouterr().out.splitlines() == ["2026-03-01 America/New_York"]
    assert _timezone(operator[0], "--add", "--from", "2026-05-01", "--zone", "Mars/Olympus") == 1
    assert "invalid_timezone" in capsys.readouterr().err


def test_timezone_prints_rebuild_reminder(operator, capsys):
    arguments = ["--add", "--from", "2026-01-01", "--zone", "America/Phoenix"]
    assert _timezone(operator[0], *arguments) == 0
    added = capsys.readouterr().out
    assert "sessionize" in added and "--rebuild" in added
    assert _timezone(operator[0], "--remove", "--from", "2026-01-01") == 0
    removed = capsys.readouterr().out
    assert "sessionize" in removed and "--rebuild" in removed
    assert _timezone(operator[0], "--list") == 0
    assert "--rebuild" not in capsys.readouterr().out


def test_timezone_does_not_rebuild(operator, engine, capsys, tmp_path):
    folder = tmp_path / "listens" / "2026"
    folder.mkdir(parents=True)
    # 03:00 UTC: 23:00 in New York, so a New York period would change nothing visible
    # unless sessions were rebuilt; the rows' computed_at proves they were not.
    records = [listen(1_780_000_000 + 60 * n, title=f"T{n}") for n in range(15)]
    (folder / "10.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records), encoding="utf-8"
    )
    listening_cli.main(["import-export", "--user", str(operator[0]), "--export", str(tmp_path)])
    listening_cli.main(["sessionize", "--user", str(operator[0]), "--rebuild"])
    capsys.readouterr()
    sessions = select(ListenSession.id, ListenSession.kind, ListenSession.computed_at).where(
        ListenSession.user_id == operator[0]
    )
    with Session(engine) as reader:
        before = reader.execute(sessions).all()
    assert before
    assert _timezone(operator[0], "--add", "--from", "2026-01-01", "--zone", "America/Phoenix") == 0
    with Session(engine) as reader:
        assert reader.execute(sessions).all() == before
