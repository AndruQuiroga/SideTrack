"""add insight events table

Revision ID: 7e0e2f720f2b
Revises: 6b1f90e2b8c7
Create Date: 2025-05-27 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e0e2f720f2b"
down_revision: Union[str, None] = "6b1f90e2b8c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "insight_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("severity", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(op.f("ix_insight_events_user_id"), "insight_events", ["user_id"], False)
    op.create_index(op.f("ix_insight_events_ts"), "insight_events", ["ts"], False)


def downgrade() -> None:
    op.drop_index(op.f("ix_insight_events_ts"), table_name="insight_events")
    op.drop_index(op.f("ix_insight_events_user_id"), table_name="insight_events")
    op.drop_table("insight_events")
