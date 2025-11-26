"""add core reboot tables"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c71e3c2f6a4b"
down_revision: str | tuple[str, ...] | None = (
    "3e1c1f4e3d90",
    "5d6e1a2b3c4d",
    "b4d9e6a8c7f2",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "core_user",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column(
            "legacy_user_id",
            sa.String(length=128),
            sa.ForeignKey("user_account.user_id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("legacy_user_id", name="uq_core_user_legacy_user_id"),
    )
    op.create_index(op.f("ix_core_user_email"), "core_user", ["email"], unique=True)

    op.create_table(
        "linked_account",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"], name="fk_linked_account_user"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "external_id", name="uq_linked_account_provider_external"
        ),
    )
    op.create_index(
        op.f("ix_linked_account_user_id"), "linked_account", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_linked_account_provider"), "linked_account", ["provider"], unique=False
    )

    op.create_table(
        "week",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=True),
        sa.Column("starts_at", sa.Date(), nullable=False),
        sa.Column("ends_at", sa.Date(), nullable=True),
        sa.Column("winning_nomination_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_week_slug"),
    )
    op.create_index(op.f("ix_week_starts_at"), "week", ["starts_at"], unique=False)

    op.create_table(
        "nomination",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("week_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("album_title", sa.String(length=256), nullable=False),
        sa.Column("artist_name", sa.String(length=256), nullable=False),
        sa.Column("album_year", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("submission_link", sa.Text(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["week_id"], ["week.id"], name="fk_nomination_week"),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"], name="fk_nomination_user"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "week_id", "user_id", name="uq_nomination_week_user"
        ),
    )
    op.create_index(op.f("ix_nomination_week_id"), "nomination", ["week_id"], unique=False)
    op.create_index(op.f("ix_nomination_user_id"), "nomination", ["user_id"], unique=False)

    op.create_table(
        "vote",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nomination_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("rank", sa.SmallInteger(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["nomination_id"], ["nomination.id"], name="fk_vote_nomination"),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"], name="fk_vote_user"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "nomination_id", "user_id", name="uq_vote_nomination_user"
        ),
    )
    op.create_index(op.f("ix_vote_user_id"), "vote", ["user_id"], unique=False)

    op.create_table(
        "rating",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("week_id", sa.Integer(), nullable=False),
        sa.Column("nomination_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("score", sa.Numeric(3, 2), nullable=False),
        sa.Column("review", sa.Text(), nullable=True),
        sa.Column("favorite_track", sa.String(length=256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["week_id"], ["week.id"], name="fk_rating_week"),
        sa.ForeignKeyConstraint(
            ["nomination_id"], ["nomination.id"], name="fk_rating_nomination"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"], name="fk_rating_user"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_id", "user_id", name="uq_rating_week_user"),
    )
    op.create_index(op.f("ix_rating_user_id"), "rating", ["user_id"], unique=False)

    op.create_table(
        "listen_event",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=True),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("legacy_listen_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"], name="fk_listen_event_user"),
        sa.ForeignKeyConstraint(["track_id"], ["track.track_id"], name="fk_listen_event_track"),
        sa.ForeignKeyConstraint(["legacy_listen_id"], ["listen.id"], name="fk_listen_event_legacy"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "legacy_listen_id", name="uq_listen_event_legacy_listen_id"
        ),
    )
    op.create_index(
        op.f("ix_listen_event_user_id"), "listen_event", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_listen_event_played_at"), "listen_event", ["played_at"], unique=False
    )

    op.create_foreign_key(
        "fk_week_winning_nomination",
        "week",
        "nomination",
        ["winning_nomination_id"],
        ["id"],
        use_alter=True,
    )


def downgrade() -> None:
    op.drop_constraint("fk_week_winning_nomination", "week", type_="foreignkey")
    op.drop_table("listen_event")
    op.drop_table("rating")
    op.drop_table("vote")
    op.drop_table("nomination")
    op.drop_table("week")
    op.drop_table("linked_account")
    op.drop_index(op.f("ix_core_user_email"), table_name="core_user")
    op.drop_table("core_user")
