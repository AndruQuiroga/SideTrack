"""add display_name and created_at to linked_accounts"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7b8f0ad4e3ab"
down_revision: str | tuple[str, ...] | None = "d90118d52e4b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "linked_accounts",
        sa.Column("display_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "linked_accounts",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.add_column("ratings", sa.Column("metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("linked_accounts", "created_at")
    op.drop_column("linked_accounts", "display_name")
    op.drop_column("ratings", "metadata")
