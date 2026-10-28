# Tasks

## 1. Remove unsupported claims with behavior coverage

- [x] 1.1 Remove computed presence and unconditional live-listener/real-time claims from club gallery and detail; add `apps/web/tests/club-data-honesty.test.cjs` with varied week counts and no update mechanism, proving neither counts nor live claims appear without evidence.
- [x] 1.2 Remove generated histogram bins and minimum positive bar widths; extend `club-data-honesty.test.cjs` for missing distributions with positive counts, unknown counts, zero ratings, supplied bins, and zero-width zero-count bars. Retain existing compatibility/profile data-honesty scenarios.

## 2. Verification and status evidence

- [x] 2.1 Run `pnpm --filter @sidetrack/web lint`, build, and test in that order; verify the existing `web/data-honesty` and authenticated-page tests still pass alongside the new rendered regression tests.
- [x] 2.2 Update `docs/status.yaml` with the passing rendered-test evidence, regenerate `docs/STATUS.md` with `uv run --frozen --extra dev python scripts/gen_status.py`, and verify `test_gen_status.py` plus `pnpm exec openspec validate fix-web-data-honesty-regressions --strict` pass. No ADR change is expected.

## Workflow follow-up

- Keep this correction separately reviewable from `rework-web-experience` and apply it before that redesign is released.
