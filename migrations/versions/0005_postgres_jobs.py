"""Install the pinned Procrastinate schema and application job records."""

from hashlib import sha256
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_postgres_jobs"
down_revision = "0004_album_genres_spotify_url"
branch_labels = None
depends_on = None


def upgrade():
    source = Path(__file__).resolve().parents[1] / "vendor" / "procrastinate-3.10.0"
    script = (source / "schema.sql").read_bytes()
    expected = (source / "schema.sha256").read_text().strip()
    if sha256(script).hexdigest() != expected:
        raise RuntimeError("Vendored Procrastinate schema checksum mismatch")
    op.execute("CREATE SCHEMA job_queue")
    op.execute("SET LOCAL search_path TO job_queue, public")
    # Upstream SQL contains function bodies; execute it as one driver statement.
    with op.get_bind().connection.driver_connection.cursor() as cursor:
        cursor.execute(script.decode("utf-8"))
    op.execute("SET LOCAL search_path TO public")
    op.create_table(
        "background_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("queue_job_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("task", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("result", sa.JSON()),
        sa.Column("error", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "job_schedules",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("task", sa.String(128), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("queue", sa.String(32), nullable=False),
        sa.Column("next_due_at", sa.DateTime(timezone=True)),
        sa.Column("interval_seconds", sa.Integer()),
    )
    op.create_index("ix_job_schedules_next_due_at", "job_schedules", ["next_due_at"])
    op.create_table(
        "job_schedule_occurrences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("schedule_id", sa.String(255), sa.ForeignKey("job_schedules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("schedule_id", "revision", "due_at"),
    )
    op.create_index("ix_job_schedule_occurrences_schedule_id", "job_schedule_occurrences", ["schedule_id"])
    op.create_table(
        "job_request_pacing",
        sa.Column("name", sa.String(32), primary_key=True),
        sa.Column("next_request_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("job_request_pacing")
    op.drop_table("job_schedule_occurrences")
    op.drop_table("job_schedules")
    op.drop_table("background_jobs")
    op.execute("DROP SCHEMA job_queue CASCADE")
