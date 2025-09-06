"""add token and role columns to user account

Revision ID: 2b6f8c1d7e90
Revises: a1b2c3d4e5f6
Create Date: 2024-10-06 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b6f8c1d7e90"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_account", sa.Column("token_hash", sa.String(length=256), nullable=True))
    op.add_column(
        "user_account",
        sa.Column("role", sa.String(length=32), nullable=False, server_default="user"),
    )


def downgrade() -> None:
    op.drop_column("user_account", "role")
    op.drop_column("user_account", "token_hash")
