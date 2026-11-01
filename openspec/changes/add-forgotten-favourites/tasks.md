## 1. Rules and read model

- [x] 1.1 Implement the versioned rule (N, W, M, K, D) and peak-window computation over included plays; verify `tests/test_rediscovery_rules.py` (qualifying track, recently played excluded, earliest max window chosen)
- [x] 1.2 Read effective session classification: autoplay excluded by default with count, `keep` override counted, `unknown` included and counted, include-autoplay toggle; verify `tests/test_rediscovery_sessions.py`
- [x] 1.3 Implement coverage and activity checks with states `not_imported`, `coverage_gap`, `insufficient_history`, `none_found`; verify `tests/test_rediscovery_coverage.py` (covered-with-zero-listens is not `not_imported`)

## 2. Storage and API

- [x] 2.1 Add `rediscovery_dismissals` model and migration with cascade from `users`; verify `services/api/tests/test_migrations.py`
- [x] 2.2 Add owner-only list, dismiss, list-dismissals and delete endpoints returning rule values, coverage range and counts; verify `services/api/tests/test_rediscovery.py`, `services/api/tests/test_personal_access.py` (404 for other members, club visibility included) and `services/api/tests/test_account_deletion.py`
- [x] 2.3 Regenerate `packages/api-client`; verify `pnpm build` passes

## 3. Web

- [x] 3.1 Build `/listening/rediscover` with the list, disclosure block, autoplay toggle, versions note, every state and dismiss/restore; verify `apps/web/tests/rediscovery.test.cjs`
- [x] 3.2 Wording and media guard: no "loved", "liked" or "your favourite", no audio elements; verify `apps/web/tests/rediscovery.test.cjs` wording case and `apps/web/app/no-fake-data.test.ts`

## 4. Owner gate

- [ ] 4.1 Owner reviews their own list on the production import, records precision (real past favourites / listed), autoplay and duplicate artefacts and any rule changes; verify the review is recorded in the docs with the rule version and the decision to link the page in navigation

## 5. Integration and status

- [ ] 5.1 Document ownership in `docs/MODULES.md`; verify `uv run --frozen --extra api --extra dev lint-imports` passes
- [ ] 5.2 Add "Forgotten favourites" to `docs/status.yaml` with evidence paths to the tests above, run `python scripts/gen_status.py` and `uv run --frozen python scripts/gen_progress.py`, then `make lint` and `make test.unit`; verify the STATUS check in CI passes
