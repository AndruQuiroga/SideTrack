"""add provenance columns to features

Revision ID: 5d6e1a2b3c4d
Revises: 9c6a1e7c1d9b
Create Date: 2025-06-02 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "5d6e1a2b3c4d"
down_revision: str | None = "9c6a1e7c1d9b"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "features",
        sa.Column("source", sa.String(length=16), nullable=False, server_default="full"),
    )
    op.add_column("features", sa.Column("seconds", sa.Float(), nullable=True))
    op.add_column("features", sa.Column("model", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("features", "model")
    op.drop_column("features", "seconds")
    op.drop_column("features", "source")
