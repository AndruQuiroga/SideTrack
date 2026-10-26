# Tasks

## 1. Honest connection states

- [x] 1.1 Require account data in ConnectionsGrid and preserve account-fetch failure as unavailable; verify rendered missing/empty/linked states and fetch failure in `apps/web/tests/connections.test.cjs`.
- [x] 1.2 Update status evidence and Phase 0 follow-up documentation; verify `gen_status.py --check`, web lint/build/tests and strict OpenSpec validation.

## Workflow follow-up

- The live Last.fm account test is explicitly deferred by the owner; do not mark credential hardening complete or archive it.
- The first rack deployment remains an operational follow-up, outside this code change.
