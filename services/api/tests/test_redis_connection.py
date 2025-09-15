import types
import pytest

import sidetrack.api.main as main
from sidetrack.config import Settings

pytestmark = pytest.mark.unit


class DummyRedis:
    def __init__(self, url: str) -> None:
        self.url = url

    def ping(self) -> bool:  # pragma: no cover - simple stub
        return True


def test_connection_refreshed_when_url_changes(monkeypatch):
    created: list[DummyRedis] = []

    def fake_from_url(url: str) -> DummyRedis:
        conn = DummyRedis(url)
        created.append(conn)
        return conn

    fake_module = types.SimpleNamespace(from_url=fake_from_url, ConnectionError=Exception)
    monkeypatch.setattr(main, "redis", fake_module)

    # reset globals
    main._REDIS_CONN = None
    main._REDIS_URL = None

    s1 = Settings(redis_url="redis://one")
    c1 = main._get_redis_connection(s1)
    c2 = main._get_redis_connection(s1)
    assert c1 is c2

    s2 = Settings(redis_url="redis://two")
    c3 = main._get_redis_connection(s2)
    assert c3 is not c1
    assert c3.url == "redis://two"
