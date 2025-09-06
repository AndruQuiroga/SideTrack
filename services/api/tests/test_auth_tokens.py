import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Ensure repository root on sys.path and configure SQLite for tests
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

from services.api.app.db import SessionLocal, engine, get_db  # noqa: E402
from services.api.app.main import app  # noqa: E402
from services.common.models import Base  # noqa: E402

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
