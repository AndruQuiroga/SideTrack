# Tasks

## 1. Compatibility

- [ ] 1.1 Add the consent flag, computation and bridge candidates. Verify that `tests/test_sound_compatibility.py` covers opt-out, small library, coverage shown, result shape (no percentage or label), bridge list and withdrawal.
- [ ] 1.2 Wire the compare page. Verify with web tests and `no-fake-data.test.ts`.
- [ ] 1.3 Update `docs/status.yaml` (the taste/compatibility row) and regenerate STATUS. Verify with `make lint` and `make test.unit`.

## Workflow follow-up

- Archive the change once every scenario has a passing test.
