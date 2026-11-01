# Tasks

## 1. Storage

- [ ] 1.1 Add `share_snapshots` and `share_links` models and a migration with cascade from users; prove with `services/api/tests/test_migrations.py` and `tests/test_share_consent.py::test_account_deletion_revokes_shares`
- [ ] 1.2 Generate tokens, store only their hashes, and redact share paths in logs; prove with `tests/test_share_consent.py::test_token_not_stored` and `::test_share_path_redacted_in_logs`

## 2. Snapshot and consent rules

- [ ] 2.1 Add the item allow-list, the default selection and `item_unavailable`; prove with `tests/test_share_consent.py::test_default_selection` and `::test_unimplemented_item_unavailable`
- [ ] 2.2 Freeze a snapshot on preview and publish only from a snapshot; prove with `::test_snapshot_frozen_after_override` and `::test_publish_without_snapshot_422`
- [ ] 2.3 Require the check-in double opt-in; prove with `::test_check_in_requires_confirmation` and `::test_default_share_has_no_check_in`
- [ ] 2.4 Reject other-member data; prove with `::test_compatibility_item_rejected`
- [ ] 2.5 State the basis (units, ranking source, sample, coverage and gate) and the mood/theme gate rule; prove with `::test_top_tracks_basis` and `::test_gate_pending_mood_unavailable`
- [ ] 2.6 Add the claim guard and the schema without free text; prove with `::test_no_prohibited_claims_any_combination`
- [ ] 2.7 Exclude identity and audio fields by default; prove with `::test_default_has_no_identity_or_audio`

## 3. Links and routes

- [ ] 3.1 Add publish, list and revoke, plus the expiry default and cap; prove with `services/api/tests/test_share_routes.py::test_revoke_returns_410_and_deletes_snapshot` and `::test_expiry_cap_422`
- [ ] 3.2 Add the public snapshot route and its open count; prove with `test_share_routes.py::test_open_records_count_only`
- [ ] 3.3 Keep visibility unchanged; prove with `test_share_routes.py::test_private_user_share_keeps_listening_404` and `::test_revoked_share_listening_still_404`
- [ ] 3.4 Add the expired-snapshot cleanup job; prove with `tests/test_share_consent.py::test_expired_snapshots_cleaned`
- [ ] 3.5 Regenerate `packages/api-client` and check boundaries; prove with `pnpm build` and `uv run --frozen --extra api --extra dev lint-imports`

## 4. Web

- [ ] 4.1 Build the share builder with exact preview, disabled Share and unavailable items; prove with `apps/web/tests/share-preview.test.cjs` (selection changed after preview, unavailable item)
- [ ] 4.2 Add the check-in confirmation dialog and the destination/retraction explanation; prove with `share-preview.test.cjs` (decline confirmation, explanation shown)
- [ ] 4.3 Add link management in settings; prove with `share-preview.test.cjs` (revoke from settings, revoke fails)
- [ ] 4.4 Build the public `/share/[token]` page with noindex, no audio, and 410/error states; prove with `share-preview.test.cjs` (valid link, revoked link) and `apps/web/app/no-fake-data.test.ts`
- [ ] 4.5 Make the builder owner-only with a sign-in redirect; prove with `share-preview.test.cjs` (signed-out builder)

## 5. Docs and status

- [ ] 5.1 Document the share rules in `docs/AUTHORIZATION.md`. Add a "Share links" item to `docs/status.yaml` with evidence `tests/test_share_consent.py`. Run `python scripts/gen_status.py` and verify the CI status check passes. No ADR is altered.
