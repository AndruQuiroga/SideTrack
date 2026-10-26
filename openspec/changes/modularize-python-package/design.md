# Design

## Context

See proposal.md. Current routes combine HTTP validation and module-owned persistence.
The migration test already compares Alembic's Postgres schema with all ORM metadata.
Phase 0 has 68 Python tests, with queued RQ functions named under services.api.jobs.

## Goals / Non-Goals

Implement ADR 0001 without an HTTP or schema change. Keep the legacy worker dormant;
Phase 2 owns its replacement. Preserve old job/import paths during rollout.

## Decisions

- Move shared config, DB/session/base, schemas, external adapters and queue plumbing
  into `sidetrack`. Keep these independent of HTTP composition. Shared enums avoid
  coupling schemas to domain initialization.
- Each domain owns its models, route handlers and services. Identity owns users,
  linked accounts and follows; catalog owns albums/tracks; listening owns listens;
  club owns weeks/nominations/votes/ratings; analysis owns features, profiles,
  compatibility and recommendations. Existing route functions remain the public
  domain operations; API composition registers them without duplicating persistence.
- Cross-domain reads use explicitly exported models. Cross-domain creation during
  ingest moves into a catalog public function; listening only creates ListenEvent.
  Shared ORM relationships retain their existing cascades and foreign keys.
- Private model, handler and service modules are protected by import-linter. Domain
  packages expose approved operations and read models; no domain imports transport
  composition or the all-model registry. Type-only relationship imports are ignored.
- The all-model registry is loaded before ORM use. Explicit legacy module aliases
  point to the same module objects, so dependency overrides, monkeypatches and old
  serialized job paths keep working. Tests use canonical imports while compatibility
  tests cover old ones. Containers use the new entrypoint.
- Capture Phase 0 OpenAPI as a fixture before moving code; compare full paths and
  schema components afterward. Existing migration drift tests prove metadata is
  unchanged. Add a cross-domain ingest test and a negative import-linter test.

Alternative: leave implementations in services and add forwarding domain packages.
Rejected because that would preserve the existing ownership problem.

## Risks / Trade-offs

- ORM registration/import cycles: use shared enums, type-only relationship imports
  and one explicit model registry; verify mapper configuration and metadata identity.
- Old jobs/imports: retain aliases rather than duplicate modules or classes.
- Existing mypy errors remain visible; do not weaken checks to hide refactor errors.
- API handlers still use FastAPI inside domain route packages. Separating transport
  from domain services more thoroughly is possible later; ownership is enforced now.

## Migration Plan

Deploy API and RQ worker together from the API image. No schema change or data move.
Rollback restores the previous image; old queued-job paths remain valid throughout.
