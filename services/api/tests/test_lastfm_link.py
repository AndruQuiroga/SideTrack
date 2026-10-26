"""Spec: identity/linked-accounts, Last.fm linking (harden-api-credentials)."""

from __future__ import annotations

import time
import urllib.parse

import httpx
import pytest
import respx
from sqlalchemy import select

from sidetrack.external import lastfm
from sidetrack.identity import LinkedAccount, User
from sidetrack.identity.link_state import STATE_TTL_SECONDS, sign_link_state
from sidetrack.types import ProviderType

from .conftest import TEST_LINK_SECRET, as_user

pytestmark = pytest.mark.unit

LASTFM_TOKEN = "a" * 32
CALLBACK_URL = "https://sidetrack.network/auth/lastfm/callback"


@pytest.fixture()
def users(db):
    a = User(display_name="User A")
    b = User(display_name="User B")
    db.add_all([a, b])
    db.flush()
    return a, b


@pytest.fixture()
def lastfm_session():
    """Mock auth.getSession; set ``.name`` and ``.key`` to control the reply."""

    class Reply:
        name = "alice"
        key = "new-session-key"

    with respx.mock(assert_all_called=False) as mock:
        mock.get(lastfm.BASE_URL).mock(
            side_effect=lambda request: httpx.Response(
                200, json={"session": {"name": Reply.name, "key": Reply.key}}
            )
        )
        yield Reply


def _lastfm_accounts(db):
    return db.scalars(
        select(LinkedAccount).where(LinkedAccount.provider == ProviderType.LASTFM)
    ).all()


def _callback(client, state, **extra):
    return client.post(
        "/integrations/lastfm/callback", json={"token": LASTFM_TOKEN, "state": state, **extra}
    )


def test_connect_returns_url_with_state(client, users):
    a, _ = users
    response = client.post(
        "/integrations/lastfm/connect",
        json={"callback_url": CALLBACK_URL},
        headers=as_user(a),
    )

    assert response.status_code == 200
    url = urllib.parse.urlsplit(response.json()["url"])
    assert f"{url.scheme}://{url.netloc}{url.path}" == "https://www.last.fm/api/auth/"
    query = dict(urllib.parse.parse_qsl(url.query))
    assert query["api_key"] == "test-lastfm-key"
    callback = urllib.parse.urlsplit(query["cb"])
    assert f"{callback.scheme}://{callback.netloc}{callback.path}" == CALLBACK_URL
    assert dict(urllib.parse.parse_qsl(callback.query))["state"]


def test_connect_refuses_another_user(client, users):
    a, b = users
    response = client.post(
        "/integrations/lastfm/connect",
        json={"user_id": str(b.id), "callback_url": CALLBACK_URL},
        headers=as_user(a),
    )
    assert response.status_code == 403


def test_connect_requires_service_token(anon_client, users):
    a, _ = users
    response = anon_client.post(
        "/integrations/lastfm/connect",
        json={"user_id": str(a.id), "callback_url": CALLBACK_URL},
    )
    assert response.status_code == 401


def test_full_flow_links_initiating_user(client, anon_client, db, users, lastfm_session):
    a, _ = users
    url = client.post(
        "/integrations/lastfm/connect",
        json={"callback_url": CALLBACK_URL},
        headers=as_user(a),
    ).json()["url"]
    cb = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))["cb"]
    state = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(cb).query))["state"]

    response = _callback(anon_client, state)

    assert response.status_code == 200
    [account] = _lastfm_accounts(db)
    assert account.user_id == a.id


def test_callback_links_state_user(anon_client, db, users, lastfm_session):
    a, _ = users
    response = _callback(anon_client, sign_link_state(a.id, TEST_LINK_SECRET))

    assert response.status_code == 200
    assert response.json()["username"] == "alice"
    [account] = _lastfm_accounts(db)
    assert (account.user_id, account.provider_user_id) == (a.id, "alice")
    assert account.access_token == "new-session-key"
    assert "new-session-key" not in response.text


def test_callback_rejects_tampered_state(anon_client, db, users, lastfm_session):
    a, _ = users
    response = _callback(anon_client, sign_link_state(a.id, "attacker-secret"))

    assert response.status_code == 400
    assert _lastfm_accounts(db) == []


def test_callback_rejects_expired_state(anon_client, db, users, lastfm_session):
    a, _ = users
    old = time.time() - STATE_TTL_SECONDS - 1
    response = _callback(anon_client, sign_link_state(a.id, TEST_LINK_SECRET, now=old))

    assert response.status_code == 400
    assert _lastfm_accounts(db) == []


def test_callback_ignores_user_id_param(anon_client, db, users, lastfm_session):
    a, b = users
    state = sign_link_state(a.id, TEST_LINK_SECRET)
    response = anon_client.post(
        f"/integrations/lastfm/callback?user_id={b.id}",
        json={"token": LASTFM_TOKEN, "state": state, "user_id": str(b.id)},
    )

    assert response.status_code == 200
    [account] = _lastfm_accounts(db)
    assert account.user_id == a.id


def test_conflict_leaves_existing_credential(anon_client, db, users, lastfm_session):
    a, b = users
    db.add(
        LinkedAccount(
            user_id=a.id,
            provider=ProviderType.LASTFM,
            provider_user_id="alice",
            display_name="alice",
            access_token="a-original-key",
        )
    )
    db.flush()

    response = _callback(anon_client, sign_link_state(b.id, TEST_LINK_SECRET))

    assert response.status_code == 409
    db.expire_all()
    [account] = _lastfm_accounts(db)
    assert account.user_id == a.id
    assert account.access_token == "a-original-key"


def test_relink_same_user_replaces_credential(anon_client, db, users, lastfm_session):
    a, _ = users
    db.add(
        LinkedAccount(
            user_id=a.id,
            provider=ProviderType.LASTFM,
            provider_user_id="alice",
            access_token="a-original-key",
        )
    )
    db.flush()

    response = _callback(anon_client, sign_link_state(a.id, TEST_LINK_SECRET))

    assert response.status_code == 200
    db.expire_all()
    [account] = _lastfm_accounts(db)
    assert account.access_token == "new-session-key"


def test_callback_get_is_gone(client, anon_client):
    url = f"/integrations/lastfm/callback?token={LASTFM_TOKEN}"
    assert client.get(url).status_code == 405
    # Only the POST callback is public.
    assert anon_client.get(url).status_code == 401
