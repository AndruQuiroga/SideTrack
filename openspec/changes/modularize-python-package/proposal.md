# Proposal

## Why

Observed: the deployed API, models, jobs and domain code live under `services/api`,
with persistence spread across transport handlers and ingest helpers. ADR 0001
already selects a modular monolith; Phase 1 implements that decision.

## What Changes

- Establish the canonical `sidetrack` package with identity, catalog, listening,
  club and analysis modules owning their models and write paths.
- Move API composition and shared infrastructure outside those domain modules.
- Route cross-domain writes through public functions, especially catalog creation
  during Last.fm ingest. Export read models explicitly for existing cross-domain queries.
- Preserve old Python import and queued-job paths as compatibility aliases.
- Enforce private module boundaries with import-linter in CI; test API/schema and
  metadata compatibility against the Phase 0 baseline.
- Update packaging, container startup, migrations, tests, commands and status docs.

Out of scope: queue replacement (Phase 2), new API behavior, API authorization
changes (Phase 3), model/column changes, audio models, dormant Spotify worker
replacement, live OAuth and rack deployment.

## Capabilities

### New Capabilities

None. This is an internal refactor and enforcement of ADR 0001, with `skip_specs: true`.

### Modified Capabilities

None. Existing API and database behavior must remain unchanged.

## Impact

Python source layout and compatibility adapters; Docker image build/startup;
Alembic model discovery; CI, Makefile and developer documentation. No migration
is needed because table metadata is preserved, verified on Postgres.
