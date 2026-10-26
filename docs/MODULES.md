# Python module boundaries

ADR 0001 is implemented in the canonical `sidetrack` package. API and Postgres worker
processes share this code; the Next.js app and Discord bot call the HTTP API.

| Module      | Owned tables                                                        |
| ----------- | ------------------------------------------------------------------- |
| `identity`  | users, linked_accounts, follows                                     |
| `catalog`   | albums, tracks                                                      |
| `listening` | listen_events, import_checkpoints                                   |
| `club`      | weeks, nominations, votes, ratings, club_notification_outbox        |
| `analysis`  | track_features, taste_profiles, compatibility, user_recommendations |

Import another domain's public package for operations or exported **read models**.
Never mutate a foreign domain's ORM instances or construct its rows. Listening
calls `catalog.resolve_listen_track` to create catalog rows, then inserts its own
ListenEvent. Existing database cascades and foreign keys remain intact.

Domain route packages own their existing HTTP operations and persistence.
`sidetrack.api` registers them and owns cross-domain read views (feed, search,
trending). Search's metadata fallback calls the public catalog function. This
preserves HTTP behavior; it does not introduce new API behavior or authorization.

`config`, `db`, `types`, `schemas`, `external`, `queue_client`, `queue_models`,
`queue_maintenance` and request pacing are shared
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
- Worker: `python -m sidetrack.worker` (CPU); see JOBS.md for queue isolation.
- Alembic imports `sidetrack.models.all_metadata`; Phase 2 adds migrations 0005–0007.

Old `services.api` imports still forward to canonical objects, including job
function aliases. Old RQ entrypoints forward to the Postgres worker; serialized
RQ jobs must be drained before cutover. The retired `services.worker` entrypoint
exits with migration instructions and never starts Spotify work. See JOBS.md for
transaction ownership, retries, schedule revisions, outbox delivery and rollback.
Shared infrastructure owns background_jobs, job_schedules, job_schedule_occurrences
and job_request_pacing. The library owns its separate job_queue schema.

Deploy API and worker together from the same image, with a matching bot. Real
audio analysis and per-user authorization remain later work. `services/extraction`
remains a stub. ROADMAP.md records deferred live OAuth and first rack deployment.
