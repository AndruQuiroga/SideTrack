"""Private dismissals for forgotten favourites (openspec: add-forgotten-favourites)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0016_rediscovery_dismissals"
down_revision = "0015_timezone_periods"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rediscovery_dismissals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("track_key", sa.String(255), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "track_key", name="uq_rediscovery_dismissal"),
        sa.CheckConstraint(
            "reason IN ('not_a_favourite', 'not_now')", name="ck_rediscovery_dismissals_reason"
        ),
    )
    op.create_index(
        "ix_rediscovery_dismissals_user_id", "rediscovery_dismissals", ["user_id"]
    )


def downgrade():
    op.drop_index("ix_rediscovery_dismissals_user_id", table_name="rediscovery_dismissals")
    op.drop_table("rediscovery_dismissals")
