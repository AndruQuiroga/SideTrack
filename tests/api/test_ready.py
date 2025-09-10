import pytest


@pytest.mark.asyncio
async def test_ready_ok(app_client):
    resp = await app_client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"ok", "degraded"}
