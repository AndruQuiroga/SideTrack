"""Spec: identity/user-preferences."""

from __future__ import annotations

import pytest

from sidetrack.identity import User
from sidetrack.types import ClubRole

from .conftest import as_user

pytestmark = pytest.mark.unit


def test_setting_a_valid_timezone(client, db, member):
    response = client.patch(
        f"/users/{member.id}", json={"timezone": "America/Phoenix"}, headers=as_user(member)
    )
    assert response.status_code == 200
    assert response.json()["timezone"] == "America/Phoenix"
    read = client.get(f"/users/{member.id}", headers=as_user(member))
    assert read.json()["timezone"] == "America/Phoenix"


def test_invalid_zone_name(client, db, member):
    member.timezone = "UTC"
    db.flush()
    response = client.patch(
        f"/users/{member.id}", json={"timezone": "Mars/Olympus"}, headers=as_user(member)
    )
    assert response.status_code == 422
    db.expire_all()
    assert db.get(User, member.id).timezone == "UTC"


def test_no_timezone_set(client, member):
    assert client.get(f"/users/{member.id}", headers=as_user(member)).json()["timezone"] is None


def test_member_cannot_edit_another_member(client, db, member, make_user):
    other = make_user("Other", role=ClubRole.MEMBER)
    response = client.patch(f"/users/{other.id}", json={"timezone": "UTC"}, headers=as_user(member))
    assert response.status_code == 403
    db.expire_all()
    assert db.get(User, other.id).timezone is None


def test_admin_sets_a_users_timezone(client, db, admin, member):
    response = client.patch(f"/users/{member.id}", json={"timezone": "UTC"}, headers=as_user(admin))
    assert response.status_code == 200
    assert response.json()["timezone"] == "UTC"


def test_admin_cannot_change_other_profile_fields(client, admin, member):
    response = client.patch(
        f"/users/{member.id}",
        json={"timezone": "UTC", "display_name": "Renamed"},
        headers=as_user(admin),
    )
    assert response.status_code == 403
