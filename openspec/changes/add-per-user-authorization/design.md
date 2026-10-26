# Design

## Context

ADR 0009 sets the model: the website holds sessions, and the API trusts named clients that
state who they act for. See proposal.md for the current state and its file references. Three
constraints shape the implementation:

- Phase 2 (`replace-rq-with-postgres-jobs`) edits the same routes (`api/routes/jobs.py`,
  `listening/routes/ingest.py`, `club/routes/weeks.py`), adds the
  `/club/notifications/*` routes and `background_jobs`, regenerates `packages/api-client`, and
  ends the Alembic chain at `0007_club_notifications`. This change starts only after Phase 2
  merges.
- Import-linter contracts (MODULES.md) allow cross-domain use only through public packages.
  Domains must not import `sidetrack.api`.
- Tests run on Postgres 16 through testcontainers. `test_migrations.py` rejects drift between
  the models and the migrations.

## Goals / Non-Goals

**Goals:**
- One place resolves the principal. Each route states its policy beside the route.
- The policy table is checked by a test against the live route list, so new routes can't
  default to open.
- Ship the API, web app and bot cut over together, with a schema rollback.

**Non-Goals:**
- Fine-grained permission storage (scopes live in code), token rotation tooling, and rate
  limiting.
- Changing response shapes beyond removing other users' data and the new error bodies.

## Decisions

**Principal resolution in `sidetrack/identity/auth.py`.** A FastAPI dependency builds
`Principal(client: ClientId, scopes: frozenset[str], actor: UUID | None)`.

- The client comes from the bearer token, compared with `hmac.compare_digest` against every
  configured token, so the check never stops early.
- The actor comes from `X-Sidetrack-Act-As`. A `discord:` subject is resolved through
  `LinkedAccount`, which is identity's own table.
- Client definitions live in code, as a mapping from client to token setting, allowed subject
  kind, actor scopes and self scopes. Tokens come from `Settings`
  (`SIDETRACK_WEB_API_TOKEN`, `SIDETRACK_BOT_API_TOKEN`, with the existing `/run/secrets`
  support).
- Alternative considered: a database `api_clients` table with hashed tokens. That adds an
  admin flow for two fixed clients, and ADR 0009 rejects it.

**Policies as dependencies, with a registry.** Each route adds
`Depends(policy("club:read"))` or something similar, and the policy dependency records itself
in the route's `dependant`. `create_app` walks `app.routes` after registration and raises if a
non-public route has no policy marker. The global `auth_middleware` only turns a missing or
unknown bearer token into 401, before routing, which keeps 401 separate from the policy-level
403 and 404.

- Alternative considered: one central path-to-policy table in middleware. It drifts from the
  routes and can't see the loaded resources. Ownership checks such as "own nomination" stay in
  the handlers, which already load the row.

**Domain-local checks through public read models.**

- `club` exposes `is_member(db, user_id)`, `member_role(db, user_id)` and the
  `require_member` and `require_admin` dependencies.
- `identity` exposes `listening_visibility(db, user_id)` and `can_view_personal(db, viewer,
  owner)`. The latter calls `club.is_member` for the `club` case.
- `listening` and `analysis` call these functions. `identity` → `club` is a new public import,
  so the protected contracts are adjusted to allow it explicitly, and `tests/test_import_boundaries.py`
  gains a case for it.

**Body `user_id` handling.** The create schemas make `user_id` optional. A helper
`resolve_owner(principal, supplied)` returns the actor, or raises 403 when the supplied value
differs. The OpenAPI contract test is updated to allow the optional field. The field is
removed in a later release.

**Membership API.** `PUT /club/members/discord/{snowflake}` with `{role}` and
`DELETE /club/members/discord/{snowflake}` (which sets `left_at`). Both use the bot self
scope `club:membership`.

- The bot calls PUT, idempotently, in its existing `ensureDiscordUser` path, with the role from
  `isAdmin`. It calls DELETE from a `guildMemberRemove` handler.
- The bot does not need the privileged members intent: membership is recorded on interaction.
- The first admin comes from `python -m sidetrack.club.admin grant-admin --discord-id <id>`,
  which writes directly through club's public function, using the operator's database access.

**Visibility of 403 versus 404.** Club gates return 403 `not_a_club_member`, because
membership is not secret to the person asking. Personal resources return 404, matching how a
missing row already behaves.

**Web BFF.**

- A server-only helper `apiForSession()` in `apps/web/app/lib/server-api.ts` reads the session
  and returns a `SidetrackApiClient` with the web token and `actAs: {user: session.user.id}`.
- Pages become server components, or call route handlers under `app/api/*`.
- The browser-side helpers in `lib/api/{discover,feed,client,social,weeks}.ts` move behind
  those handlers.
- `getApiBaseUrl()` stops reading `NEXT_PUBLIC_API_BASE_URL` in the browser, and the variable
  is removed.
- The NextAuth `jwt` callback keeps provisioning as the web client acting as itself.

**API client.** `SidetrackApiClient` gains an `actAs?: {user: string} | {discord: string}`
option and a `withActor(actor)` method that returns a client sharing the same transport. The
bot calls `client.withActor({discord: interaction.user.id})` for each interaction. The types
are regenerated with `make openapi`.

**Migration `0008_per_user_authorization` (down-revision `0007_club_notifications`).**

- Adds the `club_role` enum, and `club_members(user_id PK → users ON DELETE CASCADE, role,
  joined_at, left_at)`.
- Adds the `listening_visibility` enum, and `users.listening_visibility NOT NULL DEFAULT
  'private'`.
- Adds `background_jobs.requested_by_user_id → users ON DELETE SET NULL`.
- Seeds memberships with one `INSERT … SELECT`.
- The downgrade drops all three. `club_members` is added to the `club` row in MODULES.md.

## Risks / Trade-offs

- [The web and bot must ship with the API] → They share one stack and image tag (ADR 0006). The
  runbook gets a release note, and the stack check verifies that the new secrets are declared.
- [A stolen web token can act as any user] → Accepted in ADR 0009. The token is a Docker
  secret on the same host as the NextAuth secret, and it is never sent to the browser
  (`web/authenticated-pages` test).
- [Members who only use the website are not members until they use the bot] → The migration
  seeds active participants, and the admin CLI covers anyone else. This is documented in
  `deploy/README.md`.
- [Phase 2's routes change before this lands] → The tasks start with a rebase checkpoint that
  re-runs the route inventory. The policy test fails on any route nobody classified.
- [Hidden browser-side API calls] → A test greps the built client bundle (spec scenario) and
  covers each page in `no-fake-data.test.ts`.

## Migration Plan

1. Merge Phase 2. Rebase, and confirm that the Alembic head is `0007_club_notifications`.
2. Land the migration, principals, policies and route changes, then the API client, then the
   web app and bot. All of it goes in one PR, or in PRs that merge together before a release.
3. Deploy: create the `sidetrack_web_api_token` and `sidetrack_bot_api_token` secrets, remove
   `sidetrack_api_token`, run `alembic upgrade head`, roll out the API, web and bot images, and
   grant the first admin.
4. Rollback: roll the three images back, run `alembic downgrade 0007_club_notifications`, and
   restore the old secret.

## Open Questions

- Should leaving the guild also hide that member's past nominations and ratings from the web
  archive? The specs keep the data stored. How it's displayed can be decided later without
  changing access rules.
