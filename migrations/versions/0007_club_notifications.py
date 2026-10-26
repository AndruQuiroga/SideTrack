"""Persist club notification delivery and seed only future week deadlines."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_club_notifications"
down_revision = "0006_import_checkpoints"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "club_notification_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("week_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("schedule_id", sa.String(255), sa.ForeignKey("job_schedules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("thread_id", sa.String(32)),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("token", postgresql.UUID(as_uuid=True)),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("message_id", sa.String(32)),
        sa.Column("error", sa.String(64)),
        sa.UniqueConstraint("schedule_id", "revision"),
    )
    op.create_index("ix_club_notification_outbox_schedule_id", "club_notification_outbox", ["schedule_id"])
    # Fixed seed data; historical closed-week events must never replay at cutover.
    op.execute("""
        INSERT INTO job_schedules (id, revision, task, arguments, queue, next_due_at)
        SELECT 'club:' || w.id || ':' || e.kind, 1, 'club.notify',
               json_build_object('week_id', w.id::text, 'kind', e.kind,
                                 'deadline', e.due_at::text, 'revision', 1),
               'default', e.due_at
        FROM weeks w CROSS JOIN LATERAL (VALUES
            ('nominations-1h-reminder', w.nominations_close_at - interval '1 hour'),
            ('nominations-close', w.nominations_close_at),
            ('auto-open-poll', w.nominations_close_at),
            ('auto-open-ratings', w.poll_close_at)
        ) AS e(kind, due_at)
        WHERE e.due_at > clock_timestamp()
    """)


def downgrade():
    op.drop_table("club_notification_outbox")
    op.execute("DELETE FROM job_schedules WHERE id LIKE 'club:%'")
