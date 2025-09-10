import pytest


def test_register_password_policy(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "user1", "password": "short"},
    )
    assert resp.status_code == 400
    assert "at least 8 characters" in resp.json()["detail"]

    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "user2", "password": "alllowercase1!"},
    )
    assert resp.status_code == 400
    assert "uppercase" in resp.json()["detail"]

    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "user3", "password": "NOLOWER1!"},
    )
    assert resp.status_code == 400
    assert "lowercase" in resp.json()["detail"]

    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "user4", "password": "NoDigits!"},
    )
    assert resp.status_code == 400
    assert "digit" in resp.json()["detail"]

    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "user5", "password": "NoSpecial1"},
    )
    assert resp.status_code == 400
    assert "special" in resp.json()["detail"]

    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "valid", "password": "ValidPass1!"},
    )
    assert resp.status_code == 200


def test_register_rate_limit(client):
    for i in range(5):
        client.post(
            "/api/v1/auth/register",
            json={"username": f"rate{i}", "password": "ValidPass1!"},
        )
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "rate-final", "password": "ValidPass1!"},
    )
    assert resp.status_code == 429
