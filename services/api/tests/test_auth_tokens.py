import os

from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

from sidetrack.api.db import SessionLocal, engine, get_db  # noqa: E402
from sidetrack.api.main import app  # noqa: E402
from sidetrack.common.models import Base  # noqa: E402

Base.metadata.create_all(bind=engine.sync_engine)


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_token_flow():
    r = client.post("/api/v1/auth/register", json={"username": "alice", "password": "wonder"})
    assert r.status_code == 200
    r = client.post("/api/v1/auth/token", data={"username": "alice", "password": "wonder"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    m = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert m.status_code == 200
    assert m.json()["user_id"] == "alice"
