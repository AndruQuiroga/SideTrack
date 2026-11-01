# Tasks

## 1. API and web

- [ ] 1.1 Add read routes and regenerate `packages/api-client`; verify API tests for visibility
- [ ] 1.2 Build the mirror pages; verify `apps/web/tests/listening-mirror.test.cjs` covers n display, gap weeks and private users, and `no-fake-data.test.ts` passes

## 2. Bot

- [ ] 2.1 Add the opt-in weekly card and reaction check-ins; verify `apps/bot/tests/weekly-card.test.ts` covers opt-out and reaction
- [ ] 2.2 Update docs/status.yaml and regenerate STATUS; verify `pnpm lint`, `pnpm build` and tests

## Workflow follow-up

- Archive the change once every scenario has a passing test.
