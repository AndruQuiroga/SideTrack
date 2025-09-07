## Testing

1. Install dependencies:
   ```bash
   pip install -r requirements-dev.txt
   pip install -e .
   ```
2. Run tests:
   ```bash
   pytest -q
   ```

The database layer uses both synchronous and asynchronous SQLAlchemy engines.
`SessionLocal(async_session: bool | None = None)` returns an async session when
called inside an event loop. Pass `async_session=False` to force a synchronous
session from within async-aware code (e.g. a fixture running under
`pytest-asyncio`) to avoid `MissingGreenlet` errors.

Integration tests rely on Docker; they are automatically skipped if a Docker
daemon is not reachable.

## Environment

- Python 3.11
- SQLite database for tests
- HTTP requests mocked via `sidetrack.api.main.HTTP_SESSION`
