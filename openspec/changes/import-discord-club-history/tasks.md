# Tasks

Unchecked boxes describe implementation or execution that has **not** happened yet. Test filenames below are planned unless already present. Raw exports and participant mappings stay in protected/ignored storage; repository fixtures must be synthetic.

## 1. Source parsing and offline review

- [x] 1.1 Add club-owned export validation and stable source normalization, including allowlists, hashes, schema errors, repeated/conflicting message IDs and safe source links. Prove the source-validation scenarios in `tests/test_club_history_sources.py`; document the accepted manifest format in `docs/CLUB-HISTORY.md`.
- [x] 1.2 Parse album thread groups, source-backed winner/nomination identities, numeric and Unicode-star ratings, favorite tracks and reviews; classify templates/chat and incomplete weeks explicitly. Prove template exclusion, contradictory ratings, star precision and missing-result cases in `tests/test_club_history_parser.py`.
- [x] 1.3 Parse Singles Night session/song evidence and explicit phase/submitter mappings without name-only or chronology-only attribution. Add the reviewed date-correction mechanism and synthetic 2025-to-2026 case. Prove independent week numbers, curated headings, unknown phases and original-label preservation in `tests/test_singles_history_parser.py`; document mapping decisions in `docs/CLUB-HISTORY.md`.
- [x] 1.4 Add the operator `preview` command, canonical plan digest, message dispositions and escaped readable report. Prove deterministic output, no DB/network access, full input accounting and HTML/link safety in `tests/test_club_history_preview.py` and `tests/test_club_history_cli.py`. Verify documented example commands with synthetic exports.

## 2. Persistence, domain operations and deletion

- [x] 2.1 Add club-owned batch/source ledger mappings and the additive `Week.historical` flag with a migration after the actual current head. Prove source-key uniqueness, false defaults for existing weeks and metadata/migration agreement in `tests/test_club_history_store.py` and `services/api/tests/test_migrations.py`; update `docs/MODULES.md` ownership.
- [x] 2.2 Add separate Singles Night session, neutral song, submission and first/final rating mappings and migration constraints. Prove no invented album dependency, source-thread uniqueness, rating-phase uniqueness and independent numbering in `tests/test_singles_history_store.py` plus migration tests; document the model in `docs/CLUB-HISTORY.md`.
- [x] 2.3 Add public, transaction-owned identity provisioning and reviewed catalog upsert operations. Prove exact Discord-ID reuse, explicit new-user creation, handle collisions, private defaults, no memberships/profile overwrites, unambiguous catalog reuse and caller rollback in `tests/test_club_history_domain_operations.py`; pass `uv run --frozen --extra api --extra dev lint-imports` and document these public operations in `docs/MODULES.md`.
- [x] 2.4 Extend account-deletion behavior for imported submissions/ratings and minimal ledger replay suppression. Prove no erased-author resurrection, no deleted attribution in public reads, and preservation of another participant's song ratings in `services/api/tests/test_account_deletion.py` and `tests/test_club_history_erasure.py`.

## 3. Checked application and verification

- [x] 3.1 Add read-only `check` reconciliation, explicit insert/reuse/erased/conflict actions and target-bound plan fingerprints. Prove zero writes, unresolved-plan refusal, source/mapping changes and collisions with existing weeks/user ratings in `tests/test_club_history_check.py`; document the review output in `docs/CLUB-HISTORY.md`.
- [x] 3.2 Add one-transaction operator `apply` with expected digest, source revalidation, guild import lock and concurrent-change rejection. Prove mid-import rollback across identity/catalog/club/ledger and stale/concurrent-target failure in `tests/test_club_history_apply.py`.
- [x] 3.3 Implement source-ledger reuse and conflict protection. Prove same-plan retry, renamed files, expanded exports, edited sources/targets and all-erased replays in `tests/test_club_history_replay.py`; verify there are no duplicate entities or unapproved author creations.
- [x] 3.4 Add read-only `verify`, privacy-safe operator summaries and batch-scoped recovery documentation. Prove mismatch detection, no repair writes, no raw/local-path leakage in public output, and preservation of unrelated records in recovery-precondition tests in `tests/test_club_history_verify.py`. Document guarded reversal and backup restoration limits in `docs/CLUB-HISTORY.md`.

## 4. Historical notification isolation

- [x] 4.1 Guard historical-week reconciliation, producer and claim paths; disable stale schedules/notices while retaining source-backed dates. Prove import, later edits, restart reconciliation and obsolete pending-notice cases in `tests/test_club_history_notifications.py`, retaining existing `tests/test_club_schedules.py` and `services/api/tests/test_club_notifications.py` behavior for live weeks.
- [x] 4.2 Verify whole-import side-effect isolation across schedules, outbox, background jobs and the actual queue schema, with external sends/acquisition made fatal in tests. Prove unchanged counts and no provider exchange/download in `tests/test_club_history_side_effects.py`; add the corresponding operational checks to `docs/CLUB-HISTORY.md`.

## 5. Member-only Singles Night archive

- [x] 5.1 Add list/detail read schemas and `/club/singles-nights` routes through API composition, with member/bot policies and no ordinary mutation route. Prove member access, anonymous/non-member rejection, missing session, stable ordering and minimal response fields in `services/api/tests/test_singles_nights.py` and extend `services/api/tests/test_route_policies.py`.
- [x] 5.2 Regenerate the TypeScript client using the existing generator and add server-only Singles Night reads with session-derived actors. Prove correct endpoints, actor propagation and unavailable-state behavior in `apps/web/tests/singles-read-models.test.cjs`; pass client build and the existing browser-bundle credential guard.
- [x] 5.3 Add `/club/singles`, session details and the Club navigation link. Prove separate album/Singles Night numbering, corrected date, absent time, source links, first/final sections, deleted submitter attribution and distinct empty/unavailable/access states in `apps/web/tests/singles-archive.test.cjs`. Inspect the built pages at desktop/mobile sizes using synthetic data and document results without real participant screenshots.

## 6. Real-data rehearsal and controlled rollout

- [x] 6.1 Generate the real offline preview from the hash-verified 45-file manifest. Produce a private report accounting for all 522 distinct message IDs, the 10 album-week groups and seven Singles Night sessions, including the exact owner-confirmed date correction. Review every unresolved identity/catalog/phase decision or explicit exclusion; retain the reviewed plan digest. This is a preview, not production writes.
- [x] 6.2 Rehearse migrations, checked apply, verify, identical retry and member/non-member/anonymous archive reads on throwaway Postgres 16 + pgvector. Deliver a private rehearsal report with reviewed candidate/result counts, zero duplicate growth and unchanged delivery/membership/job counts; keep real inputs out of CI fixtures/artifacts.
- [ ] 6.3 Complete the required Python lint/module-boundary checks, relevant Postgres tests, TypeScript lint/build/tests and strict OpenSpec validation, then publish the reviewed release through CI. Deliver passing check references and a Portainer rollout plan that preserves existing env/secrets/placement and compatible API/worker/bot versions; deploy only through the maintained stack.
- [ ] 6.4 Before production application, preserve protected copies of sources/plans outside disposable `.tmp`, take a fresh database backup and restore-test it in isolation. Present exact production `check` results and batch-scoped recovery steps, then apply the approved digest once. Deliver verification evidence for actual archive records, corrected Singles Night date, attribution, absence of old notifications and preservation of unrelated links/listens; do not mark this done solely because services run.

## 7. Final evidence and status

- [ ] 7.1 Update `docs/status.yaml` to the behavior actually observed, including real provider-link verification and any remaining import gaps; regenerate `docs/STATUS.md` and the progress page. Verify `uv run --frozen python scripts/gen_status.py --check`, `uv run --frozen python scripts/check_stack_docs.py`, and `pnpm exec openspec validate import-discord-club-history --strict`; retain per-scenario evidence before archival.

## Workflow follow-up

- Keep the proposal phase separate from implementation; begin apply only after a new user request to apply this change.
- Archive only after every scenario has evidence and all required tasks are complete; then verify the resulting main specs and generated status are current.
