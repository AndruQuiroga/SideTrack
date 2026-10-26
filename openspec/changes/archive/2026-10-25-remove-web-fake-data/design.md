# Design

## Context

See proposal.md. Pages are server components fetching through `lib/api/*`; the API client throws `ApiError` with an HTTP `status`.

## Goals / Non-Goals

**Goals:** remove every invented value; one consistent "unavailable" presentation; an automated guard.

**Non-Goals:** new features, redesign, client-side retry logic.

## Decisions

**One `Unavailable` component in `components/ui.tsx`.** It takes a `what` label ("club archive", "profile") and renders a Card with a plain message. Pages use try/catch around their fetches, so data functions return real data or throw; there's no `source` field anymore. Alternative considered: result objects (`{ok, data}`). Rejected because try/catch at the page is simpler, and Next's error boundary (`app/error.tsx`) already exists for anything uncaught.

**404 vs outage.** `fetchWeekDetail` and `fetchProfileForServer` let `ApiError` propagate; pages call `notFound()` when `status === 404` and render `Unavailable` otherwise.

**Discover uses the session.** The server component reads the NextAuth session. Signed out → a sign-in prompt in place of recommendations; trending still loads.

**Guard as a node:test over source text.** `app/no-fake-data.test.ts` walks `app/**/*.{ts,tsx}` (excluding tests) and fails on banned patterns. Crude but cheap, and it runs in CI's existing `node` job. Alternative considered: an ESLint rule, which is more machinery for the same check.

## Risks / Trade-offs

- [The site looks emptier until real data exists] → That's the point; STATUS.md shows what works.
- [The guard can false-positive on legitimate words] → Patterns target identifiers (`WithFallback`, `source: 'fallback'`, `/u/demo`, `userA=demo`, `Math.random`), not English words like "placeholder" in input attributes.
