import asyncio
import pytest
from pytest_socket import enable_socket


@pytest.fixture
def event_loop():
    enable_socket()
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
