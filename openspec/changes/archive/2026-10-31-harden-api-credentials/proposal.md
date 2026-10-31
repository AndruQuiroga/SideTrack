# Proposal

## Why

The API leaks stored credentials and lets anyone attach a Last.fm account to any user. These holes exist independent of the refactor and should close before Sidetrack is deployed on Stache-Rack (ADR 0006).

## What Changes

- Linked-account responses stop including `access_token` and `refresh_token`. **BREAKING** for any client reading those fields; none in this repo do.
- Last.fm linking binds the account to the user who started it, via a signed, expiring `state` value. The `user_id` query parameter is removed. **BREAKING** for `/integrations/lastfm/callback`, which becomes a POST taking `token` and `state`.
- `POST /integrations/lastfm/connect` returns the authorization URL it builds (today it returns nothing and fails validation).
- A conflicting Last.fm link returns 409 without changing the existing account.
- The API refuses to start without `SIDETRACK_API_TOKEN` unless `SIDETRACK_ENV=development`, and compares tokens in constant time.
- Unhandled errors return a generic message with a request ID instead of the exception text.

### Out of scope

- Per-user authentication and authorization (Phase 3; GETs stay public until then).
- Encrypting stored tokens at rest (Phase 3, with the `identity` module).
- Spotify and Discord OAuth (Spotify is metadata-only per ADR 0003).

### Current state (observed)

- `LinkedAccountRead` inherits `access_token` and `refresh_token` from `LinkedAccountBase` (`services/api/schemas/core.py:46-84`), and `GET /users/{id}/linked-accounts` returns them unauthenticated (`services/api/routes/users.py:109-117`; the middleware only guards POST/PUT/PATCH/DELETE, `services/api/main.py:38-52`).
- `GET /integrations/lastfm/callback` accepts `user_id` from the query string and links the session key to that user (`services/api/routes/integrations.py:119-227`). The web page passes `user_id` straight from the URL (`apps/web/app/auth/lastfm/callback/page.tsx:29-42`).
- On conflict, the callback overwrites the existing account's token before raising 409 (`integrations.py:206-215`).
- `connect_integration` calls `_get_lastfm_auth_url` but returns `None` (`integrations.py:83-84`).
- With `SIDETRACK_API_TOKEN` unset, all writes are open (`main.py:45`).
- The 500 handler returns `str(exc)` (`main.py:68-74`).

## Capabilities

### New Capabilities

- `identity/linked-accounts`: how external accounts are linked to users and what the API reveals about them.
- `platform/api-access`: how API writes are authorized and how errors are reported.

### Modified Capabilities

None (no specs exist yet).

## Impact

- `services/api/schemas/core.py`, `services/api/routes/integrations.py`, `services/api/main.py`, `services/api/config.py`
- `apps/web/app/auth/lastfm/callback/page.tsx`, `apps/web/app/lib/api/discover.ts` (connect flow)
- `packages/api-client` types (regenerated)
- New env vars: `SIDETRACK_ENV`, `SIDETRACK_LINK_SECRET`
