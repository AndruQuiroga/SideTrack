"""Dated per-user timezone periods (openspec: add-timezone-periods)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015_timezone_periods"
down_revision = "0014_track_audio_links"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_timezone_periods",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("effective_from", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("user_timezone_periods")
