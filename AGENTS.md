## Testing

1. Install dependencies:
   ```bash
   pip install -e ".[api,extractor,scheduler,worker,dev]"
   ```
2. Run tests:
   ```bash
   pytest -q
   ```

See [`tests/README.md`](tests/README.md) for the test pyramid, markers, and
speed budgets. `pytest` skips tests marked `slow`, `gpu`, and `e2e` unless
explicitly included via `-m` or the Makefile test targets.

The database layer uses both synchronous and asynchronous SQLAlchemy engines.
`SessionLocal(async_session: bool | None = None)` returns an async session when
called inside an event loop. Pass `async_session=False` to force a synchronous
session from within async-aware code (e.g. a fixture running under
`pytest-asyncio`) to avoid `MissingGreenlet` errors.

Integration tests rely on Docker; they are automatically skipped if a Docker
daemon is not reachable.

## Redis connections

The API caches a Redis client in `sidetrack.api.main`. `_get_redis_connection`
now recreates this client whenever the `REDIS_URL` setting changes or the
existing connection is no longer reachable. When writing tests that interact
with Redis, use the `redis_conn` fixture to obtain a fresh instance and prevent
stale connections from leaking between tests.

## Environment

- Python 3.11
- PostgreSQL database for tests (via testcontainers)
- HTTP requests mocked via `sidetrack.api.main.HTTP_SESSION`
