"""Durable per-account import checkpoints."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_import_checkpoints"
down_revision = "0005_postgres_jobs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "import_checkpoints",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("provider", sa.String(32), primary_key=True),
        sa.Column("account", sa.String(255), primary_key=True),
        sa.Column("last_ts", sa.BigInteger(), nullable=False),
    )


def downgrade():
    op.drop_table("import_checkpoints")
