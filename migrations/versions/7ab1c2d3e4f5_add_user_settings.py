"""add user_settings table (base columns)

Revision ID: 7ab1c2d3e4f5
Revises: 2b6f8c1d7e90
Create Date: 2025-09-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7ab1c2d3e4f5"
down_revision: Union[str, None] = "2b6f8c1d7e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("listenbrainz_user", sa.String(length=128), nullable=True),
        sa.Column("listenbrainz_token", sa.String(length=256), nullable=True),
        sa.Column("lastfm_user", sa.String(length=128), nullable=True),
        # store Last.fm session key; column name kept as 'lastfm_api_key' for backward compatibility
        sa.Column("lastfm_api_key", sa.String(length=128), nullable=True),
        sa.Column("use_gpu", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("use_stems", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("use_excerpts", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_settings")

