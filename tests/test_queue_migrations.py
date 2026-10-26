"""Queue schema is installed by Alembic, not worker startup."""

from hashlib import sha256
from pathlib import Path

from sqlalchemy import inspect, text


def test_queue_schema_and_functions(engine):
    with engine.connect() as conn:
        tables = inspect(conn).get_table_names(schema="job_queue")
        assert "procrastinate_jobs" in tables
        assert "procrastinate_workers" in tables
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                    "WHERE n.nspname='job_queue' AND p.proname LIKE 'procrastinate_defer%'"
                )
            )
            > 0
        )
    assert {"background_jobs", "job_schedules", "job_schedule_occurrences"} <= set(
        inspect(engine).get_table_names()
    )


def test_vendored_schema_matches_pinned_distribution():
    import procrastinate

    vendor = Path(__file__).parents[1] / "migrations/vendor/procrastinate-3.10.0"
    installed = Path(procrastinate.__file__).parent / "sql/schema.sql"
    assert (vendor / "schema.sql").read_bytes() == installed.read_bytes()
    assert (
        sha256(installed.read_bytes()).hexdigest() == (vendor / "schema.sha256").read_text().strip()
    )


def test_upgrade_from_phase1_preserves_domain_rows(engine, database_url):
    import os
    from uuid import uuid4

    from alembic import command
    from alembic.config import Config

    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    user_id = uuid4()
    future_week, old_week = uuid4(), uuid4()
    try:
        command.downgrade(config, "0004_album_genres_spotify_url")
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users (id, display_name) VALUES (:id, 'Preserved')"),
                {"id": user_id},
            )
            for week_id, interval in [(future_week, "2 hours"), (old_week, "-2 hours")]:
                conn.execute(
                    text(
                        "INSERT INTO weeks (id, label, nominations_close_at, poll_close_at) "
                        "VALUES (:id, 'Cutover fixture', "
                        "clock_timestamp()+CAST(:interval AS interval), "
                        "clock_timestamp()+CAST(:interval AS interval))"
                    ),
                    {"id": week_id, "interval": interval},
                )
        command.upgrade(config, "head")
        with engine.begin() as conn:
            assert (
                conn.scalar(text("SELECT display_name FROM users WHERE id=:id"), {"id": user_id})
                == "Preserved"
            )
            conn.execute(text("DELETE FROM users WHERE id=:id"), {"id": user_id})
            assert (
                conn.scalar(
                    text("SELECT count(*) FROM job_schedules WHERE id LIKE :prefix"),
                    {"prefix": f"club:{future_week}:%"},
                )
                == 4
            )
            assert (
                conn.scalar(
                    text("SELECT count(*) FROM job_schedules WHERE id LIKE :prefix"),
                    {"prefix": f"club:{old_week}:%"},
                )
                == 0
            )
            for week_id in [future_week, old_week]:
                conn.execute(
                    text("DELETE FROM job_schedules WHERE id LIKE :prefix"),
                    {"prefix": f"club:{week_id}:%"},
                )
                conn.execute(text("DELETE FROM weeks WHERE id=:id"), {"id": week_id})
    finally:
        command.upgrade(config, "head")
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
