from __future__ import annotations

import socket

import pytest

pytest_plugins = ["services.tests.conftest"]

_MARKERS = ["unit", "integration", "contract", "slow", "gpu", "e2e"]


def pytest_configure(config: pytest.Config) -> None:
    for marker in _MARKERS:
        config.addinivalue_line("markers", f"{marker}: {marker} tests")


@pytest.fixture(autouse=True)
def _no_outbound_http(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("contract"):
        return
    allowed = {"127.0.0.1", "localhost", "::1", "testserver"}
    orig_getaddrinfo = socket.getaddrinfo

    def guard(host, *args, **kwargs):  # type: ignore[override]
        if host not in allowed:
            raise RuntimeError("Outbound HTTP blocked (mark test as contract to allow)")
        return orig_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", guard)
