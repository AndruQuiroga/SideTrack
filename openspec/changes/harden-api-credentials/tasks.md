# Tasks

## 1. Platform: token check and error responses

- [ ] 1.1 Add `env` (`SIDETRACK_ENV`) and `link_secret` (`SIDETRACK_LINK_SECRET`) to `services/api/config.py`; make `create_app` raise when the API token is missing outside development. Verify with `tests/test_api_access.py::test_startup_requires_token_in_production` and `::test_startup_allows_missing_token_in_development`.
- [ ] 1.2 Compare bearer tokens with `hmac.compare_digest` and keep the public-route list explicit. Verify with `::test_write_without_token_is_401`, `::test_write_with_wrong_token_is_401`, `::test_write_with_token_succeeds`.
- [ ] 1.3 Add the request-ID middleware and replace the 500 body with `{"error", "request_id"}`. Verify with `::test_unhandled_error_hides_internals`, which raises an exception containing a fake DB URL and asserts it's absent from the body and present in the captured log under the same ID.
- [ ] 1.4 Set `SIDETRACK_ENV=development` in `compose.yml` and `.env.example`; verify `docker compose config` shows it for the `api` service.

## 2. Identity: linked-account responses

- [ ] 2.1 Split linked-account schemas into write (accepts tokens) and read (`has_credentials`, no token fields). Verify with `tests/test_linked_accounts.py::test_list_omits_credentials` and `::test_create_response_omits_credentials`, which search the raw response text for the token value.
- [ ] 2.2 Regenerate `packages/api-client` types (`make openapi`) and drop `access_token`/`refresh_token` from hand-written `types.ts`; verify `pnpm -r build` passes.

## 3. Identity: Last.fm linking

- [ ] 3.1 Add state sign/verify helpers (HMAC-SHA256, 15-minute expiry). Verify with `tests/test_link_state.py` covering round-trip, tampered signature, expiry and malformed input.
- [ ] 3.2 Make `POST /integrations/lastfm/connect` take `{user_id, callback_url}`, return `{url}` with `state` embedded in the callback. Verify with `tests/test_lastfm_link.py::test_connect_returns_url_with_state`.
- [ ] 3.3 Convert the callback to `POST {token, state}`, link to the user in `state`, ignore any `user_id`, and check for conflicts before writing. Mock Last.fm `auth.getSession` with respx. Verify with `::test_callback_links_state_user`, `::test_callback_rejects_tampered_state`, `::test_callback_rejects_expired_state`, `::test_callback_ignores_user_id_param`, `::test_conflict_leaves_existing_credential`, `::test_relink_same_user_replaces_credential`.
- [ ] 3.4 Update the web connect flow (`apps/web/app/lib/api/discover.ts`, settings page) to start linking server-side for the session user, and make the callback page POST `{token, state}`. Verify `pnpm --filter @sidetrack/web build` passes, then manually link a Last.fm account in `docker compose up`.

## 4. Status and docs

- [ ] 4.1 Update `docs/STATUS.md` (Last.fm account link → works; Auth → partial, with per-user auth still pending) and add `SIDETRACK_ENV` and `SIDETRACK_LINK_SECRET` to `config/ENVIRONMENT.md`. Verify `pnpm exec openspec validate harden-api-credentials --strict` passes.

## Workflow follow-up

- Archive with `/opsx:archive` (or `$openspec-archive-change`) once every scenario has a passing test.
