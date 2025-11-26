from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from apps.api.db import get_engine
from apps.api.main import create_app
from apps.api.models import Base, LinkedAccount, ProviderType, User


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")
    app = create_app()
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    yield TestClient(app)

    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(client):
    engine = get_engine()
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    with TestingSessionLocal() as session:
        yield session


def _create_user(session) -> User:
    user = User(display_name="Tester", handle=f"tester-{uuid.uuid4().hex[:8]}")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_create_linked_account(client: TestClient, db_session) -> None:
    user = _create_user(db_session)
    payload = {
        "user_id": str(user.id),
        "provider": ProviderType.DISCORD.value,
        "provider_user_id": "12345678901234567",
        "display_name": "Tester#1234",
    }

    response = client.post(f"/users/{user.id}/linked-accounts", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["provider"] == ProviderType.DISCORD.value
    assert data["provider_user_id"] == payload["provider_user_id"]

    account = db_session.get(LinkedAccount, uuid.UUID(data["id"]))
    assert account is not None
    assert account.user_id == user.id


def test_discord_provider_requires_snowflake(client: TestClient, db_session) -> None:
    user = _create_user(db_session)
    payload = {
        "user_id": str(user.id),
        "provider": ProviderType.DISCORD.value,
        "provider_user_id": "not-a-snowflake",
    }

    response = client.post(f"/users/{user.id}/linked-accounts", json=payload)

    assert response.status_code == 422


def test_spotify_requires_future_expiry(client: TestClient, db_session) -> None:
    user = _create_user(db_session)
    expired_payload = {
        "user_id": str(user.id),
        "provider": ProviderType.SPOTIFY.value,
        "provider_user_id": "spotify-user",
        "access_token": "token",
        "token_expires_at": datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat(),
    }

    response = client.post(
        f"/users/{user.id}/linked-accounts", json=expired_payload
    )
    assert response.status_code == 422

    future_payload = expired_payload | {
        "token_expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    }

    ok_response = client.post(
        f"/users/{user.id}/linked-accounts", json=future_payload
    )
    assert ok_response.status_code == 201


def test_duplicate_provider_user_id_is_blocked(client: TestClient, db_session) -> None:
    user_one = _create_user(db_session)
    user_two = _create_user(db_session)
    payload = {
        "user_id": str(user_one.id),
        "provider": ProviderType.DISCORD.value,
        "provider_user_id": "12345678901234567",
    }

    first = client.post(f"/users/{user_one.id}/linked-accounts", json=payload)
    assert first.status_code == 201

    second = client.post(f"/users/{user_two.id}/linked-accounts", json=payload)
    assert second.status_code == 409


def test_lookup_user_by_provider_id(client: TestClient, db_session) -> None:
    user = _create_user(db_session)
    payload = {
        "user_id": str(user.id),
        "provider": ProviderType.DISCORD.value,
        "provider_user_id": "12345678901234567",
    }
    client.post(f"/users/{user.id}/linked-accounts", json=payload)

    lookup = client.get(
        f"/users/lookup/by-provider/{payload['provider']}/{payload['provider_user_id']}"
    )

    assert lookup.status_code == 200
    assert lookup.json()["id"] == str(user.id)


def test_delete_linked_account(client: TestClient, db_session) -> None:
    user = _create_user(db_session)
    payload = {
        "user_id": str(user.id),
        "provider": ProviderType.DISCORD.value,
        "provider_user_id": "12345678901234567",
    }
    client.post(f"/users/{user.id}/linked-accounts", json=payload)

    delete_response = client.delete(
        f"/users/{user.id}/linked-accounts/{payload['provider']}/{payload['provider_user_id']}"
    )
    assert delete_response.status_code == 204

    remaining = db_session.scalars(select(LinkedAccount)).all()
    assert remaining == []
