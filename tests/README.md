# Testing Strategy

## Test Pyramid

```
       e2e smoke (3–5 flows)
      -----------------------
      integration (API+DB+Redis)
      --------------------------
      contract (HTTP clients)
      -----------------------
      unit (pure funcs, adapters)
```

- **Unit**: pure functions and adapters. Target 60–70% of the suite. Keep each test under 1s.
- **Contract**: stubbed HTTP clients to external APIs with snapshot responses. Use when an
  external contract is important but full integration would be flaky.
- **Integration**: exercises FastAPI with TimescaleDB and Redis, but no internet access.
  Keep each test ≤10s and cover only critical paths.
- **E2E smoke**: docker-compose a minimal stack and walk 3–5 critical flows
  (`/health`, `/api/v1/ingest/listens`, `/tags/lastfm/sync`, `/analyze/track/{id}`,
  `/score/track/{id}`, `/api/v1/dashboard/*`). These are slow and run nightly.

## Markers & Speed Budget

- `@pytest.mark.unit` – default; < 1s each
- `@pytest.mark.contract` – stubbed HTTP clients
- `@pytest.mark.integration` – API + DB + Redis; ≤10s each
- `@pytest.mark.e2e` – full stack smoke tests
- `@pytest.mark.slow` – anything exceeding the budgets
- `@pytest.mark.gpu` – requires a GPU

`pytest` excludes `slow`, `gpu`, `e2e`, and `contract` by default. Use `-m` to include them when needed.

## Adding Tests

1. Prefer unit tests; add contract/integration/e2e only when necessary.
2. Snapshot HTTP responses for contract tests to detect upstream changes.
3. Integration tests must run offline; mock external calls.
4. E2E smoke tests should spin up the minimal compose stack and cover the flows above.

## Fixtures & Factories

- Shared factories live in [`tests/factories`](factories/README.md).
- Service‑specific fixtures belong in `apps/<service>/tests/conftest.py`.
- Use the `redis_conn` fixture for Redis and `SessionLocal` for DB access.
- Mark heavy fixtures with `slow` or `gpu` as appropriate.

## Running Tests

Use the make targets:

```
make test.unit       # unit tests
make test.contract   # contract tests
make test.int        # integration tests
make test.e2e        # end-to-end smoke
make test.all        # everything
```
