import pytest


@pytest.mark.asyncio
async def test_health_ok(app_client):
    resp = await app_client.get("/health")
    assert resp.status_code == 200

