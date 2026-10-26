# 0009: Per-user API authorization

- Status: accepted (implemented by `add-per-user-authorization`, 2026-10-26)
- Date: 2026-10-25

## Context

Observed today (`sidetrack/api/main.py`): one shared bearer token (`SIDETRACK_API_TOKEN`)
guards POST/PUT/PATCH/DELETE; every GET is anonymous. The web app and the bot both hold
that token, so the API cannot tell which client called or which person the call is for.
Writes take `user_id` from the request body (nominations, votes, ratings, listen events,
Last.fm ingest), so any token holder can act as anyone. Anyone who can reach the API can
read every user's listening history, linked accounts, taste profiles and ballots.

People sign in only through the web app (NextAuth with Discord, JWT sessions,
`apps/web/app/lib/auth.ts`). The bot sees Discord users and maps them to Sidetrack users by
Discord ID (`apps/bot/src/clubService.ts`). Some web client components call the API
straight from the browser (`NEXT_PUBLIC_API_BASE_URL`). There is one club (one Discord guild),
and the schema has no membership or role data. Bot admin rights come from Discord
permissions (`isAdmin` in `apps/bot/src/runtime/handlers.ts`).

## Decision

**The web server is the only place that holds user sessions. The API trusts named service
clients that state which user they are acting for.** The API does no OAuth itself and issues
no tokens.

1. **Client credentials.** Each caller has its own bearer token, read from an env var or Docker
   secret: `SIDETRACK_WEB_API_TOKEN` and `SIDETRACK_BOT_API_TOKEN`. Each client's allowed
   scopes are fixed in code (`sidetrack/identity`). Tokens are compared in constant time.
   The shared `SIDETRACK_API_TOKEN` is retired. The API refuses to start outside development
   if a configured client has no token, or if two clients share one.
2. **Acting for a user.** A client names the user with `X-Sidetrack-Act-As`:
   - The web app sends `user:<uuid>`, taken only from the server-side NextAuth session.
   - The bot sends `discord:<snowflake>`, taken only from the Discord interaction. The API
     resolves it through `linked_accounts`.
   - Each client may use only its own form; the API rejects the other with 403. Without the
     header, the request runs as the client itself, with only service scopes.
3. **What a client can do while acting for a user.**
   - The web app may use every user-level operation.
   - The bot is limited to club and catalog operations. It never reads listening data, linked
     accounts or analysis.
   - A stolen bot token can therefore cast club votes in members' names, but it cannot read
     personal data. A stolen web token can do anything a user can; the web container already
     holds the NextAuth secret, so this does not widen the trust boundary.
4. **No anonymous access**, except `GET /health` and `POST /integrations/lastfm/callback`
   (protected by the signed `state` added in `harden-api-credentials`). Every route
   declares an access policy. A route without a policy is denied, and a test enumerates all
   registered routes against the policy table.
5. **Identity comes from the principal, not the body.** Writes take the user from the acting
   principal. A body or query `user_id` that differs from the actor gets 403. These fields
   stay in the schema for one release as optional and deprecated.
6. **Responses.**
   - 401: missing or unknown client credential.
   - 403: not allowed (missing scope, wrong act-as form, not a club member, body user mismatch).
   - 404: a personal resource the actor may not see, so its existence isn't revealed.
   - Logs record the client ID and actor ID with the request ID, never the tokens.

### Ownership and visibility

Club membership is a new `club_members` table owned by `club`, with role `member` or
`admin`. The bot is its only writer (service scope `club:membership`). The bot upserts the
member and their role whenever a guild member uses it, deriving the role from the same Discord
permission check it uses today, and it marks a member as left when they leave the guild.
Signing in on the web does not make anyone a member. A one-off CLI (`python -m sidetrack.club_admin grant-admin`) grants the first admin.
The migration adds existing users as members if they have a linked Discord account and any
nomination, vote or rating.

Each user gets a new `users.listening_visibility` setting: `private` (the default) or `club`.

| Domain | Read | Write |
| --- | --- | --- |
| identity: user profile (name, handle) | self; club members see members | self; create and Discord-lookup are the `identity:provision` service scope (web sign-in, bot) |
| identity: linked accounts | self only, always | self; Last.fm via signed state |
| identity: follows | club members | self as follower |
| club: weeks, nominations, ratings, summaries, trending | club members | members nominate and rate as themselves; edit or withdraw own nomination; admins create and edit weeks, override winners, delete ratings; the bot service may set only week thread IDs |
| club: votes (ballots) | the voter's own ballot only | members vote as themselves |
| club: notification outbox | bot service only | bot service only |
| catalog: albums, search | any authenticated principal | members create, resolve and enrich; admins edit |
| listening: listen events, recent listening | self; club members when the owner chose `club` | self (import and ingest) |
| analysis: taste profiles | self; club members when the owner chose `club` | self (recompute) |
| analysis: recommendations | self only | none |
| analysis: compatibility | either of the two users, if both are members and the other user chose `club` | none |
| analysis: track features | `analysis:write` service scope; no client holds it today (ADR 0001: the GPU worker calls code directly) | same |
| jobs: status | the user who submitted the job | none |

Cross-domain checks use public read models: `club.is_member`/`club.member_role`, and an
identity visibility read model. This keeps the import-linter contracts intact.

### Migration path for endpoints that are public today

Sidetrack has never been deployed (ADR 0006 rollout is pending), so the cutover ships as one
release of the API, web app and bot together. There is no long dual-mode period.

1. The migration after Phase 2's head (`0008_per_user_authorization`, down-revision
   `0007_club_notifications`) adds `club_members`, `users.listening_visibility` and
   `background_jobs.requested_by_user_id`, and seeds existing members.
2. The API adds principals, policies and the per-route table, with the new failure codes.
3. The web app moves every browser-side API call behind Next.js server code (route handlers or
   server components) that sends the web token and `user:<session id>`. Anonymous visitors
   see a sign-in prompt instead of the club archive. API CORS then allows no browser origins.
4. The bot switches to its own token and sends `discord:<id>` on every interaction-driven call.
5. `SIDETRACK_API_TOKEN` is deleted from config, Compose, the Swarm stack and docs.
   Rollback means rolling back all three images and downgrading the migration.

## Consequences

- Phase 3's implementation starts after Phase 2 merges, because it edits the same routes,
  the generated client and the Alembic chain.
- The club archive is no longer public. A public read-only archive would need a new ADR.
- Ballots become secret. Tallies and results endpoints are separate work.
- Encrypting stored provider tokens at rest, deferred from `harden-api-credentials`, remains
  Phase 3 work but is a separate change.
- A future native or mobile client would need API-issued user tokens and a new ADR. This
  design deliberately has none.
