# Proposal

## Why

The web app shows invented data whenever the API fails, and some invented values even when it succeeds. That's the same failure that hid the mocked models: the site looks like it works when it doesn't. AGENTS.md now forbids it.

## What Changes

- Remove the sample weeks, demo feed, placeholder profile (including `Math.random()` timeline values), demo blend tracks and demo recommendations and trending. When the API fails, pages show an explicit "unavailable" state.
- A week that doesn't exist returns 404; an API outage shows the unavailable state (today both show sample weeks).
- Remove values the API didn't compute: the default "72%" compatibility badge on profiles, the default shared artists and genres on the compare page, and the "<genre> essentials" recommendation cards.
- Remove links to the nonexistent `demo` / `demo2` users (navbar "Demo Profile", home page, compare page, command palette, profile page).
- Discover requests recommendations for the signed-in user instead of the literal user `demo`, and asks visitors to sign in.
- Copy that claims features which don't exist (taste metrics "based on Spotify/Last.fm audio features") is corrected.
- A unit test fails if fallback or demo data patterns return to `apps/web/app`.

### Out of scope

- Making the social features (feed, blend, compare, recommendations) actually work; they show their real API state.
- Redesigning pages.

### Current state (observed)

- `apps/web/app/lib/api/weeks.ts:48-220`, `feed.ts:30-81`, `profile.ts:36-153`: fallback generators, used by `page.tsx`, `club/page.tsx`, `club/weeks/[id]/page.tsx`, `feed/page.tsx`, `u/[id]/page.tsx`.
- `blend/page.tsx:12-58`, `discover/page.tsx:19-99`: inline demo data; discover calls `fetchRecommendations('demo')`.
- `compare/page.tsx:56-57`: default shared artists and genres; `u/[id]/page.tsx:45`: compatibility defaults to 72%.
- Demo-user links: `components/navbar.tsx:17-20`, `page.tsx:61,88`, `compare/page.tsx:188`, `components/command-palette.tsx:206`, `u/[id]/page.tsx:73,246`.

## Capabilities

### New Capabilities

- `web/data-honesty`: what the web app may display when data is missing or the API is unavailable.

### Modified Capabilities

None.

## Impact

- `apps/web/app/**` (lib/api, pages, components); no API or schema changes.
