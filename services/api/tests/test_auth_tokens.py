import pytest


@pytest.mark.asyncio
async def test_token_flow(async_client):
    r = await async_client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "wonder"}
    )
    assert r.status_code == 200
    r = await async_client.post(
        "/api/v1/auth/token", data={"username": "alice", "password": "wonder"}
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    m = await async_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert m.status_code == 200
    assert m.json()["user_id"] == "alice"
