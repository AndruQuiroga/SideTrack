# Design

## Context

See proposal.md for the holes and their locations. The web app already holds the service token server-side (`apps/web/app/lib/auth.ts`) and knows the signed-in user's Sidetrack ID through NextAuth, so it can start the Last.fm flow server-side for that user. The Last.fm callback runs in the browser, where the service token must not be exposed.

## Goals / Non-Goals

**Goals:**
- Close the three holes with minimal surface change, ahead of the Phase 1 restructure.
- Make every spec scenario a pytest test.

**Non-Goals:**
- Per-user sessions in the API (Phase 3).
- Moving code into the `identity` module (Phase 1 does that; this change edits files in place).

## Decisions

**Signed state with the standard library.** `state = base64url(json{"u": user_id, "exp": unix_ts, "n": nonce}) + "." + base64url(hmac_sha256(secret, payload))`, verified with `hmac.compare_digest`. Lifetime 15 minutes. Alternatives: `itsdangerous` (a new dependency for about 30 lines) or a server-side state table (needs storage and cleanup). Replay within 15 minutes can only re-link the same Last.fm account to the same user, which is idempotent.

**`SIDETRACK_LINK_SECRET` separate from the API token.** The API token is shared with three clients; the link secret never leaves the API. In development mode it defaults to a random per-process value, so links break on restart, which is acceptable there.

**Callback becomes POST, listed as a public write.** The callback is state-changing, so it shouldn't be a GET. Its authorization comes from `state`, not the bearer token, so it joins `/health` in the middleware's public list. The browser page POSTs `{token, state}` as JSON.

**`has_credentials` replaces token fields in read schemas.** Split `LinkedAccountBase` into a write schema (accepts tokens) and a read schema (`has_credentials: bool`, `token_expires_at`). A computed field derives `has_credentials` from the ORM row, so no column is added.

**Startup check in `create_app`.** Settings gain `env: Literal["development", "production"] = "production"`. `create_app` raises `RuntimeError` when the token is missing outside development. Token comparison uses `hmac.compare_digest`.

**Request IDs.** A middleware assigns `X-Request-ID` (or reuses a valid incoming one, at most 64 characters of `[A-Za-z0-9-]`), stores it on `request.state`, echoes it in the response header and includes it in the 500 body and log line.

## Risks / Trade-offs

- [Existing deployments without a token stop starting] → `SIDETRACK_ENV=development` is set in `compose.yml` and `.env.example`; the change 2 stack sets real secrets.
- [The web callback page breaks if deployed before the API] → Ship the API and web together; both live in this repo and one stack.
- [Tests run on SQLite, while production is Postgres] → No Postgres-specific behaviour here. Moving the test DB to Postgres is a separate Phase 0 item.

## Migration Plan

1. Deploy API and web together. Existing linked accounts keep working; only how they're displayed and how new links are made changes.
2. Rollback: revert the commit. No schema migration is involved.
