# Proposal

## Why

Observed: anyone who can reach the API can read every user's listening history, linked
accounts, taste profiles and ballots, because GETs are anonymous (`sidetrack/api/main.py`,
`auth_middleware` guards only mutating methods). The one shared service token cannot say who a
write is for: nominations, votes, ratings, listen events and Last.fm ingest take `user_id` from
the request body (`sidetrack/schemas/core.py`). ADR 0009 sets out per-user authorization. It has
to land before the Stache-Rack rollout (ADR 0006) exposes the API.

## What Changes

- **BREAKING:** Retire the shared `SIDETRACK_API_TOKEN`. Each client gets its own token
  (`SIDETRACK_WEB_API_TOKEN`, `SIDETRACK_BOT_API_TOKEN`) with scopes fixed in code.
- Clients act for a user through `X-Sidetrack-Act-As`. The web app sends `user:<uuid>` from
  its server session. The bot sends `discord:<snowflake>` and is limited to club and catalog
  operations.
- **BREAKING:** Every route except `GET /health` and `POST /integrations/lastfm/callback` needs
  a client credential. Every route declares an access policy, and a route without one is
  denied.
- **BREAKING:** Writes take the user from the acting principal. A body or query `user_id` that
  doesn't match gets 403.
- Add club membership with `member` and `admin` roles. The bot maintains it. Club data is
  visible to members only. Ballots are visible only to the person who cast them. Admin
  operations check the stored role.
- Add a per-user `listening_visibility` setting (`private` by default, or `club`). It controls
  who can see listen history, taste profiles and compatibility. Linked accounts and
  recommendations stay owner-only, and job status is visible only to the user who submitted
  the job.
- **BREAKING:** The web app stops calling the API from the browser. Anonymous visitors see a
  sign-in prompt, not the club archive. API CORS no longer allows browser origins.
- The bot authenticates as itself and acts for the Discord user on each interaction.
- Add migration `0008_per_user_authorization` on top of Phase 2's `0007_club_notifications`.
  It adds `club_members`, `users.listening_visibility` and
  `background_jobs.requested_by_user_id`, and seeds existing club participants as members.

### Out of scope

- Encrypting stored provider tokens at rest. This is Phase 3, but a separate change.
- API-issued user tokens, API-side OAuth, and native or mobile clients (ADR 0009).
- A public read-only club archive, vote tallies and results endpoints, and club phase
  enforcement.
- Multiple clubs. There is one guild today.
- Live verification against real Discord and Last.fm accounts, and the first rack deployment
  (both still deferred from Phase 0).

### Current state

- Observed: the auth middleware only checks writes, against one token
  (`sidetrack/api/main.py`). `PUBLIC_WRITE_PATHS` holds only the Last.fm callback.
- Observed: the web app forwards that service token from server code
  (`apps/web/app/lib/server-env.ts`). Client components (`apps/web/app/blend/page.tsx`,
  `components/club-gallery.tsx`, `command-palette.tsx`, `connections-grid.tsx`) call
  `NEXT_PUBLIC_API_BASE_URL` straight from the browser.
- Observed: the bot provisions users by Discord ID and sends `user_id` in nomination, vote and
  rating bodies (`apps/bot/src/clubService.ts`). It decides admin rights from Discord
  permissions (`isAdmin`, `apps/bot/src/runtime/handlers.ts`).
- Observed: there is no club or membership table (`sidetrack/club/models.py`), and no
  visibility field on users (`sidetrack/identity/models.py`).
- Assumed, to be verified during implementation: no page outside those listed calls the API
  from the browser.

## Capabilities

### New Capabilities

- `platform/api-authorization`: how callers authenticate, how they act for a user, the default
  deny rule and the failure codes.
- `club/membership-access`: club membership and roles, and who can read or change club data.
- `identity/personal-data-visibility`: who can see a user's linked accounts, listening data,
  taste, compatibility, recommendations and jobs.
- `web/authenticated-pages`: how the website handles anonymous visitors and keeps API
  credentials on the server.

### Modified Capabilities

None in `openspec/specs/`. The unarchived `harden-api-credentials` change adds a
`platform/api-access` requirement, "Writes require the service token", which this change
supersedes. If that change is archived first, this change's delta gains a REMOVED entry for
it (see tasks).

## Impact

- Python: `sidetrack/api/main.py`, `sidetrack/config.py`, new `sidetrack/identity/auth.py`,
  route modules in every domain, `sidetrack/club` membership, the schemas, and migration
  `0008_per_user_authorization`.
- TypeScript: `packages/api-client` (act-as option, regenerated types), the web data layer and
  pages that call the API, and the bot client set-up and `clubService`.
- Config and deploy: new secrets, removal of `SIDETRACK_API_TOKEN` from `.env.example`,
  `compose.yml`, `deploy/stack.yml`, `config/ENVIRONMENT.md` and `deploy/README.md`.
- Docs: STATUS (Auth row), MODULES (`club_members` ownership), ROADMAP.
- Sequencing: implementation starts after `replace-rq-with-postgres-jobs` merges, because both
  changes edit the jobs, ingest and weeks routes, the API client and the Alembic chain.
