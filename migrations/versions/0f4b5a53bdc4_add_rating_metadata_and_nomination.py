"""Add rating metadata, nomination link, and timestamps.

Revision ID: 0f4b5a53bdc4
Revises: d90118d52e4b
Create Date: 2025-01-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0f4b5a53bdc4"
down_revision: Union[str, None] = "d90118d52e4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ratings",
        sa.Column(
            "nomination_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "ratings",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
    )
    op.add_column("ratings", sa.Column("metadata", sa.JSON(), nullable=True))
    op.create_foreign_key(
        "fk_ratings_nomination_id",
        "ratings",
        "nominations",
        ["nomination_id"],
        ["id"],
        ondelete="SET NULL",
    )



def downgrade() -> None:
    op.drop_constraint("fk_ratings_nomination_id", "ratings", type_="foreignkey")
    op.drop_column("ratings", "metadata")
    op.drop_column("ratings", "created_at")
    op.drop_column("ratings", "nomination_id")
