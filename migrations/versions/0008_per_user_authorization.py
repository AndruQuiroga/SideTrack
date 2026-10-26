"""Per-user authorization: club membership, listening visibility, job submitters (ADR 0009)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_per_user_authorization"
down_revision = "0007_club_notifications"
branch_labels = None
depends_on = None

club_role = postgresql.ENUM("member", "admin", name="club_role", create_type=False)
listening_visibility = postgresql.ENUM("private", "club", name="listening_visibility", create_type=False)


def upgrade():
    bind = op.get_bind()
    club_role.create(bind, checkfirst=False)
    listening_visibility.create(bind, checkfirst=False)

    op.create_table(
        "club_members",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", club_role, nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "users",
        sa.Column("listening_visibility", listening_visibility, nullable=False, server_default="private"),
    )
    op.add_column(
        "background_jobs",
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    # Existing participants keep access: a linked Discord account plus any club activity.
    op.execute("""
        INSERT INTO club_members (user_id, role, joined_at)
        SELECT u.id, 'member', clock_timestamp()
        FROM users u
        WHERE EXISTS (SELECT 1 FROM linked_accounts la WHERE la.user_id = u.id AND la.provider = 'discord')
          AND (EXISTS (SELECT 1 FROM nominations n WHERE n.user_id = u.id)
               OR EXISTS (SELECT 1 FROM votes v WHERE v.user_id = u.id)
               OR EXISTS (SELECT 1 FROM ratings r WHERE r.user_id = u.id))
    """)


def downgrade():
    op.drop_column("background_jobs", "requested_by_user_id")
    op.drop_column("users", "listening_visibility")
    op.drop_table("club_members")
    bind = op.get_bind()
    listening_visibility.drop(bind, checkfirst=False)
    club_role.drop(bind, checkfirst=False)
