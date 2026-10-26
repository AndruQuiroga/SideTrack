"""Spec: club/membership-access, how membership is recorded."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from services.api.tests.conftest import WEB, as_discord, as_user, snowflake
from sidetrack.club import ClubMember, Nomination, is_member, member_role
from sidetrack.types import ClubRole

pytestmark = pytest.mark.unit


def test_bot_records_member_with_role(bot_client, make_user, db):
    discord_id = snowflake()
    user = make_user("Guild admin", discord_id=discord_id)

    response = bot_client.put(f"/club/members/discord/{discord_id}", json={"role": "admin"})

    assert response.status_code == 200
    assert member_role(db, user.id) is ClubRole.ADMIN
    # Idempotent, and a later call can change the role.
    bot_client.put(f"/club/members/discord/{discord_id}", json={"role": "member"})
    assert member_role(db, user.id) is ClubRole.MEMBER


def test_unlinked_discord_user_is_404(bot_client):
    response = bot_client.put(f"/club/members/discord/{snowflake()}", json={"role": "member"})
    assert response.status_code == 404


def test_web_cannot_grant_membership(app, make_user, db):
    from fastapi.testclient import TestClient

    discord_id = snowflake()
    user = make_user("Web user", discord_id=discord_id)
    with TestClient(app, headers=WEB) as web:
        acting = web.put(
            f"/club/members/discord/{discord_id}", json={"role": "admin"}, headers=as_user(user)
        )
        itself = web.put(f"/club/members/discord/{discord_id}", json={"role": "admin"})
    assert (acting.status_code, itself.status_code) == (403, 403)
    assert db.get(ClubMember, user.id) is None


def test_bot_acting_for_a_user_cannot_change_membership(bot_client, make_user):
    discord_id = snowflake()
    make_user("Member", role=ClubRole.MEMBER, discord_id=discord_id)
    response = bot_client.put(
        f"/club/members/discord/{discord_id}",
        json={"role": "admin"},
        headers=as_discord(discord_id),
    )
    assert response.status_code == 403


def test_member_leaves_guild_keeps_history(bot_client, client, make_user, admin, db):
    discord_id = snowflake()
    user = make_user("Leaver", role=ClubRole.MEMBER, discord_id=discord_id)
    album = client.post(
        "/albums/", json={"title": "Kept", "artist_name": "Band"}, headers=as_user(user)
    ).json()
    week = client.post("/weeks/", json={"label": "Leave week"}, headers=as_user(admin)).json()
    nomination = client.post(
        f"/weeks/{week['id']}/nominations",
        json={"album_id": album["id"], "week_id": week["id"]},
        headers=as_user(user),
    ).json()

    response = bot_client.delete(f"/club/members/discord/{discord_id}")

    assert response.status_code == 204
    assert not is_member(db, user.id)
    assert db.get(Nomination, nomination["id"]) is not None
    # Rejoining restores membership.
    bot_client.put(f"/club/members/discord/{discord_id}", json={"role": "member"})
    assert is_member(db, user.id)


def test_first_admin_command(make_user, db):
    from sidetrack.club_admin import grant_admin

    discord_id = snowflake()
    user = make_user("Owner", discord_id=discord_id)
    assert grant_admin(db, discord_id=discord_id) == user.id
    assert member_role(db, user.id) is ClubRole.ADMIN

    other = make_user("Second")
    grant_admin(db, user_id=other.id)
    assert member_role(db, other.id) is ClubRole.ADMIN
    with pytest.raises(LookupError):
        grant_admin(db, user_id=uuid4())


def test_migration_seeds_active_discord_users(engine, database_url):
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    active, idle, no_discord = uuid4(), uuid4(), uuid4()
    week, album = uuid4(), uuid4()
    try:
        command.downgrade(config, "0007_club_notifications")
        with engine.begin() as conn:
            for user_id, name in [(active, "A"), (idle, "B"), (no_discord, "C")]:
                conn.execute(
                    text("INSERT INTO users (id, display_name) VALUES (:id, :name)"),
                    {"id": user_id, "name": name},
                )
            for user_id, discord in [(active, snowflake()), (idle, snowflake())]:
                conn.execute(
                    text(
                        "INSERT INTO linked_accounts (id, user_id, provider, provider_user_id) "
                        "VALUES (:id, :user, 'discord', :discord)"
                    ),
                    {"id": uuid4(), "user": user_id, "discord": discord},
                )
            conn.execute(
                text("INSERT INTO albums (id, title, artist_name) VALUES (:id, 'LP', 'Band')"),
                {"id": album},
            )
            conn.execute(
                text("INSERT INTO weeks (id, label, winner_album_id) VALUES (:id, 'W', :album)"),
                {"id": week, "album": album},
            )
            for user_id in (active, no_discord):
                conn.execute(
                    text(
                        "INSERT INTO ratings (id, week_id, user_id, album_id, value) "
                        "VALUES (:id, :week, :user, :album, 4)"
                    ),
                    {"id": uuid4(), "week": week, "user": user_id, "album": album},
                )
        command.upgrade(config, "head")
        with engine.begin() as conn:
            members = set(conn.scalars(text("SELECT user_id FROM club_members")))
            assert active in members
            assert idle not in members
            assert no_discord not in members
            assert (
                conn.scalar(
                    text("SELECT listening_visibility::text FROM users WHERE id=:id"),
                    {"id": active},
                )
                == "private"
            )
    finally:
        command.upgrade(config, "head")
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM weeks WHERE id=:id"), {"id": week})
            conn.execute(text("DELETE FROM albums WHERE id=:id"), {"id": album})
            conn.execute(
                text("DELETE FROM users WHERE id = ANY(:ids)"), {"ids": [active, idle, no_discord]}
            )
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
