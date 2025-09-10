"""add track features embeddings scores tables and materialized views

Revision ID: b4d9e6a8c7f2
Revises: 9c6a1e7c1d9b
Create Date: 2024-06-02 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "b4d9e6a8c7f2"
down_revision: str | None = "9c6a1e7c1d9b"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # track_features table
    op.create_table(
        "track_features",
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("sr", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("rms", sa.Float(), nullable=True),
        sa.Column("tempo", sa.Float(), nullable=True),
        sa.Column("key", sa.String(length=16), nullable=True),
        sa.Column("mfcc", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("spectral", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "dataset_version",
            sa.String(length=16),
            nullable=False,
            server_default="v1",
        ),
        sa.ForeignKeyConstraint(["track_id"], ["track.track_id"],),
        sa.PrimaryKeyConstraint("track_id", "dataset_version"),
    )

    # track_embeddings table
    op.create_table(
        "track_embeddings",
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("dim", sa.Integer(), nullable=False),
        sa.Column("vec", Vector(None), nullable=True),
        sa.Column("norm", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "dataset_version",
            sa.String(length=16),
            nullable=False,
            server_default="v1",
        ),
        sa.ForeignKeyConstraint(["track_id"], ["track.track_id"],),
        sa.PrimaryKeyConstraint("track_id", "model", "dataset_version"),
    )

    # track_scores table
    op.create_table(
        "track_scores",
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["track_id"], ["track.track_id"],),
        sa.PrimaryKeyConstraint("track_id", "metric", "model"),
    )

    # materialized view for weekly centroids
    op.execute(
        sa.text(
            """
            CREATE MATERIALIZED VIEW mv_weekly_centroids AS
            SELECT
                date_trunc('week', created_at) AS week,
                model,
                avg(vec) AS centroid,
                count(*) AS track_count
            FROM track_embeddings
            GROUP BY week, model
            """
        )
    )

    # materialized view for 90-day outliers
    op.execute(
        sa.text(
            """
            CREATE MATERIALIZED VIEW mv_outliers_90d AS
            SELECT
                track_id,
                model,
                value,
                created_at
            FROM track_scores
            WHERE metric = 'outlier'
              AND created_at >= (now() - interval '90 days')
            """
        )
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_outliers_90d")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_weekly_centroids")
    op.drop_table("track_scores")
    op.drop_table("track_embeddings")
    op.drop_table("track_features")
