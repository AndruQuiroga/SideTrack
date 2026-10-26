"""Spec: identity/linked-accounts, credential exposure (harden-api-credentials)."""

from __future__ import annotations

import pytest

from sidetrack.identity import LinkedAccount, User
from sidetrack.types import ProviderType

from .conftest import as_user

pytestmark = pytest.mark.unit

SESSION_KEY = "lastfm-session-key-4f1c9a"


@pytest.fixture()
def user(db):
    user = User(display_name="Listener")
    db.add(user)
    db.flush()
    return user


def test_list_omits_credentials(client, db, user):
    db.add(
        LinkedAccount(
            user_id=user.id,
            provider=ProviderType.LASTFM,
            provider_user_id="alice",
            display_name="alice",
            access_token=SESSION_KEY,
        )
    )
    db.flush()

    response = client.get(f"/users/{user.id}/linked-accounts", headers=as_user(user))

    assert response.status_code == 200
    assert SESSION_KEY not in response.text
    [item] = response.json()
    assert item["provider"] == "lastfm"
    assert item["provider_user_id"] == "alice"
    assert item["display_name"] == "alice"
    assert item["has_credentials"] is True
    assert "access_token" not in item
    assert "refresh_token" not in item


def test_list_reports_missing_credentials(client, db, user):
    db.add(
        LinkedAccount(
            user_id=user.id,
            provider=ProviderType.DISCORD,
            provider_user_id="123456789012345678",
        )
    )
    db.flush()

    [item] = client.get(f"/users/{user.id}/linked-accounts", headers=as_user(user)).json()

    assert item["has_credentials"] is False


def test_create_response_omits_credentials(client, user):
    response = client.post(
        f"/users/{user.id}/linked-accounts",
        json={
            "user_id": str(user.id),
            "provider": "lastfm",
            "provider_user_id": "bob",
            "access_token": SESSION_KEY,
            "refresh_token": "refresh-secret-77",
        },
        headers=as_user(user),
    )

    assert response.status_code == 201
    assert SESSION_KEY not in response.text
    assert "refresh-secret-77" not in response.text
    assert response.json()["has_credentials"] is True
