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

The database layer uses both synchronous and asynchronous SQLAlchemy engines. `SessionLocal()` attempts to return an `AsyncSession` when an event loop is running, otherwise a synchronous `Session`.

## Environment

- Python 3.11
- SQLite database for tests
- HTTP requests mocked via `sidetrack.api.main.HTTP_SESSION`
