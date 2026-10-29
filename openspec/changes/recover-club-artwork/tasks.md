# Tasks

## 1. Artwork discovery

- [x] 1.1 Add exact Spotify entity artwork discovery and conservative artist/title matching, with reviewed MusicBrainz/CAA fallback and insufficient-identity rejection; prove exact-link, conflicting-link, edition ambiguity and unavailable-provider cases in `tests/test_artwork_discovery.py` using synthetic responses.
- [x] 1.2 Add bounded HTTPS/image-host/redirect validation, lookup deduplication and rate-limit handling; prove unsafe destination, missing image, oversized/non-image response and exhausted-retry behavior in `tests/test_artwork_discovery.py`.
- [x] 1.3 Add private canonical preview reports that record exact target/provider identities and unresolved reasons without writes; prove deterministic output, digest integrity and redaction in `tests/test_artwork_cli.py`, and document commands/provider prerequisites in `docs/ARTWORK.md`.

## 2. Persistence and guarded recovery

- [x] 2.1 Add catalog-owned cover/evidence operations, separate club-owned SinglesSongArtwork storage and recovery receipts with an additive migration; verify Postgres schema parity/cascade deletion in `services/api/tests/test_migrations.py` and `tests/test_artwork_store.py`, without changing legacy song snapshots.
- [x] 2.2 Implement check/apply/verify and guarded artwork-only reversal through public domain operations; prove digest checks, stale-target atomic rejection, existing-cover preservation, identical retry, deleted-target handling and reversal guards in `tests/test_artwork_apply.py` and `tests/test_artwork_cli.py`.
- [x] 2.3 Prove original history verification/replay/erasure behavior after artwork recovery, unchanged protected records and zero delivery/job side effects in `tests/test_artwork_history_compatibility.py`; run existing club-history suites and `lint-imports`, and document the compatibility/reversal boundary in `docs/ARTWORK.md`.

## 3. API and archive presentation

- [x] 3.1 Expose optional song cover URLs through existing member-gated Singles Night detail reads, regenerate the additive API contract and TypeScript client; prove cover/null output, no evidence leaks and unchanged 200/403/401 access in `services/api/tests/test_singles_nights.py` and API-client actor tests.
- [x] 3.2 Render Singles Night covers with descriptive alt text, image-error/unavailable states and responsive sizing while retaining album cover behavior; prove rendering/read models/access states in `apps/web/tests/singles-archive.test.cjs` and `singles-read-models.test.cjs`, run the browser credential guard and inspect synthetic desktop/mobile previews.
- [x] 3.3 Document API artwork semantics and unavailable behavior in `docs/ARTWORK.md`; verify generated client build, web lint/build/tests and API contract checks.

## 4. Production recovery and evidence

- [ ] 4.1 Produce a protected production inventory/preview with exact recoverable, existing, conflicting and unavailable counts; resolve only evidence-backed identities and rehearse the checked plan on an isolated restored database, retaining a report proving coverage, unchanged history and successful retry.
- [ ] 4.2 Add the rollout/guarded-reversal runbook, run required lint/type/import/status/OpenSpec checks and relevant Postgres/web suites, and publish reviewed passing images; verify CI and immutable image revisions before rollout.
- [ ] 4.3 Capture a fresh backup with successful isolated restoration and a protected production baseline; deploy migration/API before web through the existing Portainer stack, apply the checked artwork plan and retain verification of coverage, original history, access controls, image display and unchanged protected records/side effects. Preserve compatible unrelated service pins and actual recovery evidence outside Git.
- [ ] 4.4 Update `docs/status.yaml`, regenerate `docs/STATUS.md`, and record actual coverage, unresolved records and verification paths in committed documentation; verify `scripts/gen_status.py --check`, strict OpenSpec validation and every claimed evidence path.
