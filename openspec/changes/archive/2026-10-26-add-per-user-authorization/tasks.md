# Tasks

## 0. Sequencing checkpoint

- [x] 0.1 Confirm that `replace-rq-with-postgres-jobs` has merged to main. Rebase this branch, then confirm the Alembic head is `0007_club_notifications` (`uv run --frozen --extra api alembic heads`). Regenerate the route inventory with `uv run --frozen --extra api python scripts/gen_status.py`, and record in design.md any route added since this plan that the policy table doesn't classify.

## 1. Schema

- [x] 1.1 Add migration `0008_per_user_authorization`. It creates `club_role` and `club_members` (club models), adds `users.listening_visibility` (identity models) and `background_jobs.requested_by_user_id`, and seeds memberships. Prove upgrade from 0007, downgrade, and model/migration agreement in `services/api/tests/test_migrations.py`. Prove the seeding rule in `tests/test_club_membership.py::test_migration_seeds_active_discord_users`. Add `club_members` to MODULES.md and `tests/test_module_layout.py` table ownership.

## 2. Principals and policies

- [x] 2.1 Add the per-client token settings, retire `api_token`, and add the start-up checks for missing and duplicate tokens. Prove them in `services/api/tests/test_api_access.py::test_startup_requires_each_client_token`, `::test_startup_rejects_duplicate_tokens` and `::test_shared_token_is_rejected`. Update `services/api/tests/test_runtime_config.py` for `/run/secrets` reading of both tokens.
- [x] 2.2 Implement `sidetrack/identity/auth.py`: principal resolution, `X-Sidetrack-Act-As` parsing for both subject kinds, per-client subject restrictions, and the 401/400/403 responses. Prove them in `services/api/tests/test_principals.py`, covering anonymous GET, unknown token, the wrong subject form, an unknown Discord subject and a malformed header.
- [x] 2.3 Add the `policy()` dependency, the start-up check for routes without a policy, the public-route allowlist, and the authorization log line with client and actor. Prove them in `services/api/tests/test_route_policies.py`, which builds an app with an unclassified route, compares every registered route with the policy table in `docs/AUTHORIZATION.md`, and checks the log line without the token in it. Write `docs/AUTHORIZATION.md` as the policy table.
- [x] 2.4 Remove credentialed CORS origins from the API. Prove it in `services/api/tests/test_api_access.py::test_preflight_allows_no_browser_origin`.

## 3. Club access

- [x] 3.1 Add the club membership public functions, the `require_member`/`require_admin` dependencies, the `PUT`/`DELETE /club/members/discord/{id}` routes and the `python -m sidetrack.club_admin grant-admin` command. Prove the bot upsert, the web being refused, leaving the guild (data retained) and the first-admin command in `tests/test_club_membership.py`.
- [x] 3.2 Apply member-only policies to weeks, nominations, ratings, summaries and trending, and apply admin policies to week management, the admin routes and album edits, with the bot limited to thread IDs. Use actor-owned writes for nominations, votes and ratings, and owner-or-admin for nomination edits. Prove every scenario of `club/membership-access` in `services/api/tests/test_club_access.py`, and update `test_weeks.py`, `test_nominations.py` and `test_votes.py` to send principals.
- [x] 3.3 Make ballots private: `/votes` lists only the actor's votes, and another member's vote returns 404. Restrict the notification routes to the bot acting as itself. Prove both in `services/api/tests/test_club_access.py::test_votes_private` and in `services/api/tests/test_club_notifications.py::test_web_cannot_claim`.

## 4. Personal data access

- [x] 4.1 Add the identity visibility read model, the `listening_visibility` patch (self only), owner-only linked accounts, provisioning-scope user creation and provider lookup, and self-only follows. Prove them in `services/api/tests/test_personal_access.py`, and update `test_linked_accounts.py` and `test_lastfm_link.py`: connect takes the user from the actor, not the body.
- [x] 4.2 Apply visibility to listen events, recent listening and taste profiles. Make imports, ingest and recompute owner-only. Record `requested_by_user_id` when a job is submitted, and make job status visible only to the submitter. Prove these scenarios in `services/api/tests/test_personal_access.py` and `services/api/tests/test_jobs.py::test_status_only_for_submitter`.
- [x] 4.3 Make recommendations owner-only. Compatibility requires membership plus consent. Feed and search are scoped to the actor. Prove them in `services/api/tests/test_personal_access.py`. Add the identity → club public import to the import-linter contracts, with a case in `tests/test_import_boundaries.py`, and run `uv run --frozen --extra api --extra dev lint-imports`.
- [x] 4.4 Make body `user_id` optional and check it against the actor in every create schema. Update the OpenAPI contract allowance in `tests/test_job_compatibility.py`/`tests/test_module_layout.py`, and prove the mismatch and omission scenarios in `services/api/tests/test_principals.py::test_body_user_mismatch` and `::test_body_user_omitted`.

## 5. Clients

- [x] 5.1 Add `actAs` and `withActor()` to `packages/api-client` and regenerate the types (`make openapi`). Prove the header in a new `packages/api-client` unit test. Run `pnpm -r build`.
- [x] 5.2 Bot: read `SIDETRACK_BOT_API_TOKEN` (and `_FILE`), act for `discord:<id>` on every interaction-driven call, upsert membership with the `isAdmin` role in `ensureDiscordUser`, and record leaving on `guildMemberRemove`. Prove these in `apps/bot/tests/act-as.test.ts`, with doubles under `tests/` only. Run `pnpm --filter @sidetrack/bot lint test build`.
- [x] 5.3 Web: add the server-only `apiForSession()`, move the browser-side API calls (blend, club gallery, command palette, connections grid, discover, feed, weeks) behind server components or route handlers, add sign-in and not-a-member states, and remove `NEXT_PUBLIC_API_BASE_URL`. Prove every scenario of `web/authenticated-pages` in `apps/web/tests/authenticated-pages.test.ts`, including a scan of the built client bundle, and keep `apps/web/app/no-fake-data.test.ts` passing. Run `pnpm --filter @sidetrack/web lint build`.

## 6. Configuration, docs and integration

- [x] 6.1 Replace `SIDETRACK_API_TOKEN` with the two client secrets in `.env.example`, `compose.yml`, `deploy/stack.yml`, `config/ENVIRONMENT.md` and `deploy/README.md` (cutover, rollback and first admin). Prove this with `scripts/check_stack_docs.py` and `docker compose config`.
- [x] 6.2 Integration: with Compose on migrated Postgres, check that an anonymous GET returns 401, that a member's actions through the bot and the web are attributed correctly, and that a non-member gets refused. Then run `make lint`, `make test.unit`, the full API suite, `pnpm -r run lint test build`, `lint-imports` and `pnpm exec openspec validate add-per-user-authorization --strict`.
- [x] 6.3 Update `docs/status.yaml` (the Auth row, with test evidence) and regenerate `docs/STATUS.md`. Mark ADR 0009 accepted, and update the Phase 3 section of ROADMAP.md. Prove it with `uv run --frozen --extra api python scripts/gen_status.py --check` and `services/api/tests/test_gen_status.py`. Regenerate the progress page (`scripts/gen_progress.py`).

## Workflow follow-up

- If `harden-api-credentials` is archived before this change, add a `## REMOVED Requirements` entry to a `specs/platform/api-access/spec.md` delta for "Writes require the service token" (Reason: superseded by `platform/api-authorization`; Migration: per-client tokens). Re-run strict validation before archiving.
- Archive with `/opsx:archive` once every scenario has a passing test.
- Next Phase 3 change: encrypt stored provider tokens at rest.
