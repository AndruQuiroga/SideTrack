"""Add unique constraint for listen event deduplication.

Revision ID: 0003_listen_event_dedup
Revises: 0002_thread_ids_string
Create Date: 2026-02-24
"""

from alembic import op

revision = "0003_listen_event_dedup"
down_revision = "0002_thread_ids_string"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_listen_event_dedup",
        "listen_events",
        ["user_id", "track_id", "played_at"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_listen_event_dedup", "listen_events", type_="unique")
