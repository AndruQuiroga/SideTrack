# Tasks

## 1. Guard first

- [x] 1.1 Add `apps/web/app/no-fake-data.test.ts` that scans `app/**/*.{ts,tsx}` for banned patterns and names offending files. Verify it fails on the current code (`pnpm --filter @sidetrack/web test`).

## 2. Data layer

- [x] 2.1 Remove sample/demo generators and `*WithFallback` from `lib/api/weeks.ts`, `feed.ts`, `profile.ts`; drop the `source` field. Verify `pnpm --filter @sidetrack/web build` type-checks.
- [x] 2.2 Add an `Unavailable` component to `components/ui.tsx`.

## 3. Pages

- [x] 3.1 Home, club archive, week detail (404 vs unavailable), feed and profile (404 vs unavailable) use real fetches with `Unavailable` on error; remove the `fallback` badges in `week-card.tsx` and `week-detail.tsx`. Verify with the build and the guard test.
- [x] 3.2 Profile: remove the default compatibility badge, the fabricated "essentials" cards and the claim about audio features; show taste metrics only when present. Verify with the guard test and a build.
- [x] 3.3 Blend: show an error with no tracks on failure. Compare: no default shared artists or genres. Discover: session user's recommendations, sign-in prompt when signed out, no demo content. Verify with the build and the guard test.
- [x] 3.4 Remove demo-user links from the navbar, home page, compare page, command palette and profile page. Verify the guard test passes.

## 4. Status

- [x] 4.1 Update `docs/STATUS.md` (web fallback data → removed). Verify `pnpm exec openspec validate remove-web-fake-data --strict` and the full web test suite pass.
