# Python module boundaries

ADR 0001 is implemented in the canonical `sidetrack` package. API and RQ worker
processes share this code; the Next.js app and Discord bot call the HTTP API.

| Module      | Owned tables                                                        |
| ----------- | ------------------------------------------------------------------- |
| `identity`  | users, linked_accounts, follows                                     |
| `catalog`   | albums, tracks                                                      |
| `listening` | listen_events                                                       |
| `club`      | weeks, nominations, votes, ratings                                  |
| `analysis`  | track_features, taste_profiles, compatibility, user_recommendations |

Import another domain's public package for operations or exported **read models**.
Never mutate a foreign domain's ORM instances or construct its rows. Listening
calls `catalog.resolve_listen_track` to create catalog rows, then inserts its own
ListenEvent. Existing database cascades and foreign keys remain intact.

Domain route packages own their existing HTTP operations and persistence.
`sidetrack.api` registers them and owns cross-domain read views (feed, search,
trending). Search's metadata fallback calls the public catalog function. This
preserves HTTP behavior; it does not introduce new API behavior or authorization.

`config`, `db`, `types`, `schemas`, `external`, `queue` and `jobs` are shared
infrastructure. Shared enums and one Base registry avoid duplicate types.
`sidetrack.models` composes mappings for Alembic and mapper initialization; domain
code must not import that registry or HTTP composition.

## Enforcement and verification

Run `uv run --frozen --extra api --extra dev lint-imports`. Five protected contracts
restrict imports of domain internals; one forbidden contract prevents domains from
importing composition, the registry or legacy services. API composition alone may
register private route modules. Type-only relationship annotations are excluded.
See import-linter's [protected-contract documentation](https://import-linter.readthedocs.io/en/latest/contract_types/protected/).

`tests/test_import_boundaries.py` runs the guard against real source and disposable
copies containing illegal imports. `test_module_layout.py` verifies table ownership,
legacy object identity, worker compatibility and the frozen Phase 0 OpenAPI contract.
`test_ingest_boundary.py` verifies catalog resolution and listen insertion against
migrated Postgres. Existing migration tests reject metadata drift.

## Startup and compatibility

- API: `uvicorn sidetrack.api.main:create_app --factory`
- Worker: `python -m sidetrack.rq_worker`
- Alembic imports `sidetrack.models.all_metadata`; this move requires no migration.

Old `services.api` paths forward to the same canonical objects, including serialized
`services.api.jobs.*` jobs. New jobs keep those serialized names too, so a rollback
to the previous image can still consume them. Old worker startup remains valid. Keep adapters during
rollout; removal needs a later change. Deploy API and worker together with the same
image. Rollback uses the previous image and the unchanged database schema.

`services/worker` is dormant and undeployed; Phase 2 owns its replacement/removal.
`services/extraction` remains a stub. Queue replacement, real audio analysis and
per-user API authorization are outside Phase 1. ROADMAP.md records deferred live
OAuth verification and first rack deployment; neither is claimed complete.
