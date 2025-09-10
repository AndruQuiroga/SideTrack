"""add dataset_version columns for features and embeddings

Revision ID: 9c6a1e7c1d9b
Revises: 7e0e2f720f2b
Create Date: 2025-06-01 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9c6a1e7c1d9b"
down_revision: str | None = "7e0e2f720f2b"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("features", sa.Column("dataset_version", sa.String(length=16), nullable=False, server_default="v1"))
    op.drop_constraint("features_track_unique", "features", type_="unique")
    op.create_unique_constraint("features_track_dataset_unique", "features", ["track_id", "dataset_version"])

    op.add_column("embeddings", sa.Column("dataset_version", sa.String(length=16), nullable=False, server_default="v1"))
    op.drop_constraint("embeddings_track_model_unique", "embeddings", type_="unique")
    op.create_unique_constraint(
        "embeddings_track_model_dataset_unique",
        "embeddings",
        ["track_id", "model", "dataset_version"],
    )


def downgrade() -> None:
    op.drop_constraint("embeddings_track_model_dataset_unique", "embeddings", type_="unique")
    op.create_unique_constraint("embeddings_track_model_unique", "embeddings", ["track_id", "model"])
    op.drop_column("embeddings", "dataset_version")

    op.drop_constraint("features_track_dataset_unique", "features", type_="unique")
    op.create_unique_constraint("features_track_unique", "features", ["track_id"])
    op.drop_column("features", "dataset_version")
