# Tasks

## 1. API and projection

- [ ] 1.1 Add read routes, including the original-space neighbour route, and regenerate `packages/api-client`. Verify with API tests for visibility and the check-in-owner-only rule.
- [ ] 1.2 Add the projection job with `projection_version` and invalidation. Verify that `tests/test_projection.py` covers deterministic PCA, version recording and invalidation on a corpus change.

## 2. Web

- [ ] 2.1 Build the mirror pages with table alternatives and the shared state component. Verify that `apps/web/tests/listening-mirror.test.cjs` covers n display, gap weeks, the stale model, projection label, original-space neighbours, table view, reduced motion and private users. Verify that `no-fake-data.test.ts` passes.

## 3. Bot

- [ ] 3.1 Add the opt-in weekly DM card and reaction check-ins. Verify that `apps/bot/tests/weekly-card.test.ts` covers opt-out, DMs blocked, the thin-week card and reactions.
- [ ] 3.2 Update `docs/status.yaml` and regenerate STATUS. Verify with `pnpm lint`, `pnpm build` and the tests.

## Workflow follow-up

- Archive the change once every scenario has a passing test.
