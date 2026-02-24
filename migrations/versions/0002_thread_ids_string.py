"""Change week thread ID columns from BigInteger to String(32).

Discord snowflake IDs exceed JavaScript's safe integer range (2^53).
Storing them as strings prevents silent precision loss.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002_thread_ids_string"
down_revision: str | Sequence[str] | None = "0001_canonical_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    "nominations_thread_id",
    "poll_thread_id",
    "winner_thread_id",
    "ratings_thread_id",
)


def upgrade() -> None:
    for col in _COLUMNS:
        op.alter_column(
            "weeks",
            col,
            existing_type=sa.BigInteger(),
            type_=sa.String(32),
            existing_nullable=True,
            postgresql_using=f"{col}::text",
        )


def downgrade() -> None:
    for col in _COLUMNS:
        op.alter_column(
            "weeks",
            col,
            existing_type=sa.String(32),
            type_=sa.BigInteger(),
            existing_nullable=True,
            postgresql_using=f"{col}::bigint",
        )
