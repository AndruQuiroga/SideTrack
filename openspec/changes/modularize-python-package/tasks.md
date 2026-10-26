# Tasks

## 1. Canonical package and ownership

- [x] 1.1 Move shared infrastructure and domain models/handlers into sidetrack; preserve legacy module identity and API contract. Verify `tests/test_module_layout.py` and the existing API/Postgres migration tests; document ownership in `docs/MODULES.md`.
- [x] 1.2 Move catalog writes out of listening ingest into a public catalog function; verify `tests/test_ingest_boundary.py` proves catalog track creation and listen persistence still work on Postgres.

## 2. Runtime and enforcement

- [x] 2.1 Update packaging, Alembic, API/worker startup, Docker, CI and Makefile for the canonical package; verify import-linter, API image build and canonical/legacy entrypoint smoke tests.
- [x] 2.2 Protect module internals and prevent domain imports of transport/registry; verify `tests/test_import_boundaries.py` fails on an injected cross-domain private import and passes on the real source.
- [x] 2.3 Update AGENTS.md, README, module documentation, roadmap and generated status evidence; run Python/web checks, strict OpenSpec validation and `gen_status.py --check`, retaining the deferred live checks as partial.

Verification on 2026-10-25: 85 Python tests, 11 web tests and 4 bot tests pass.
Workspace lint/build, Ruff, all six import contracts, strict OpenSpec validation,
deployment-document coverage and the generated-status check pass. The API image
loads canonical/legacy imports, applies all migrations to temporary Postgres 16,
and returns a healthy response. Temporary containers/network were removed.
Mypy reports 40 errors in the canonical package and remains non-blocking; this
change does not claim to resolve the recorded type-checking backlog.

## Workflow follow-up

- Open a separate PR stacked on the Phase 0 follow-up. Do not merge either PR automatically.
- Preserve old import paths for queued jobs during rollout; remove aliases only in a later explicit change.
