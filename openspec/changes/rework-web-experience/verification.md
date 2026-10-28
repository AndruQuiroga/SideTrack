# Journal implementation verification

Reviewed 2026-10-28. This records the implemented application separately from the earlier studies. Screenshots use fictional records confined to `apps/web/tests/fixtures/`; production code has no fixture mode.

## Checks

Web lint, production build and **59 web tests pass**, including existing access guards, built-bundle credential boundaries and five data-honesty regressions. Workspace `pnpm lint` and `pnpm build` pass for web, bot and API client. Commands: `pnpm --filter @sidetrack/web lint`, `pnpm --filter @sidetrack/web build`, `pnpm --filter @sidetrack/web test`, `pnpm lint`, `pnpm build`.

Contrast tests parse actual theme variables: normal text meets 4.5:1 against both surfaces; control boundaries meet 3:1. Final boundary colors are `#82877b` light and `#646b62` dark. Georgia/system font fallbacks need no download.

Status was regenerated from YAML; all seven `services/api/tests/test_gen_status.py` tests pass. Both `rework-web-experience` and `fix-web-data-honesty-regressions` pass strict OpenSpec validation. Changed application/status files pass `git diff --check`.

## Browser evidence

The isolated harness runs the production Next build with loopback-only test API/session services. It never initiates real provider linking. After building, run `node apps/web/tests/browser-harness.cjs` from the repository root; its frame endpoint embeds the actual app at the specified width without substituting styles.

| ID | Observed result |
| --- | --- |
| B01 | Desktop Overview and archive inspected in both themes. Sidebar, editorial hierarchy, artwork, neutral sections and persisted full-theme switching work. Desktop mobile-menu control is hidden. |
| B02 | Actual 320/390px frames reflow without horizontal overflow (DOM client width equals scroll width). Week identity, schedule, reviews and history remain readable. At 320px, keyboard Enter opens Menu and selecting Club closes it. Pointer selection also closes it. CSS provides 44px coarse-pointer controls. |
| B03 | Search modal autofocuses input; Tab stays within it; Escape restores Search focus. Filled-input Escape has a regression test and final-build browser check. Search error remains visible with Retry; metadata-only matches have no dead links. |
| B04 | Filtered archive URL initializes query/sort/view. Highest rated places older Soft Geometry first while Latest winner remains Night Transit. Detail, explicit return and browser Back preserve state. No-match Clear filters restores the archive. |
| B05 | Signed-out archive preserves encoded filters through login. No real OAuth submission; normalized callback URL verified by handler tests. |
| B06 | Non-member shows members-only; offline Account shows unavailable; empty current week invents no album/deadline/action; partial Overview retains personal history when Club fails. |
| B07 | Actual image 404 becomes Artwork unavailable while preserving title and geometry. |
| B08 | Account shows supplied Last.fm identity and metadata-only legacy Spotify information, without Spotify connect. Failed local Last.fm initiation leaves an inline error. |
| B09 | Unknown week displays shared not-found at 320px. Loading/error screens preserve the shell. |

Reduced-motion CSS was reviewed: its media query suppresses animation/transitions and the design requires no decorative motion. Runtime OS preference emulation was unavailable, so this is source verification, not an emulated-browser claim. These checks are not complete accessibility certification.

## Every delta scenario

Test names below refer to files under `apps/web/tests/`.

| Spec scenarios | Evidence |
| --- | --- |
| Member navigation; Search entry; Mobile navigation | `application-navigation.test.cjs` destinations/current state; B01–B03 |
| Signed-out overview; Independent section failure | `application-navigation.test.cjs` signed-out no-fetch/independent sections; B06 |
| Legacy blend URL; Existing archive link | `application-navigation.test.cjs`, `authenticated-pages.test.cjs`; B04 |
| Return to filtered archive; External return URL | `discord-sign-in.test.cjs` normalized callback and unsafe URL matrix; B05 |
| Scheduled future week; No scheduled weeks | `club-read-models.test.cjs` future/null/tie ordering; `club-browsing.test.cjs` empty context; B06 |
| Share a filtered archive; No matches; Rating sort does not replace the newest winner | `club-archive-state.test.cjs` URL round-trip, rated/unrated sorting, latest-winner independence; B04 |
| Winner is not the first nomination; Winner has no artwork | `club-read-models.test.cjs` stored winner/override/catalog failure/deduplication; `interface-presentation.test.cjs` missing/invalid artwork; B07 |
| Available discussion destination; No discussion destination | `club-browsing.test.cjs` valid/missing thread links, UTC schedules, no inferred permissions, reviews before nominations |
| Ratings request fails | `club-read-models.test.cjs`, `club-browsing.test.cjs` optional failure versus empty; `club-data-honesty.test.cjs` absent histogram |
| Shared visual language | `interface-presentation.test.cjs` landmarks/title/sections/contrast; B01–B02 |
| Connection lookup fails; Empty account list; Connection choices | `connections.test.cjs` failed/empty/supplied accounts and legacy Spotify controls; B06/B08 |
| Search keyboard journey; Record without a destination | `search-dialog.test.cjs` metadata, empty/error, abort and Escape; B03 |
| Narrow week page; Reduced motion | B02/B09; production reduced-motion CSS review described above |
| Owner opens Listening; Another private history | `listening-history.test.cjs` session owner and signed-out/private/error matrix |
| Crossing a UTC day; Older page | `listening-history.test.cjs` offsets/midnight, invalid input, 50-row pagination and user preservation; B02 |
| No imported records; Import coverage unknown | `listening-history.test.cjs` empty records and no unsupported coverage/live/source promises |

## Local performance

Five authenticated complete HTTP response samples against the isolated production server:

| Route | Milliseconds | Median |
| --- | --- | --- |
| Overview | 39, 27, 42, 33, 33 | 33 |
| Archive | 62, 31, 48, 46, 21 | 46 |
| Week | 25, 31, 37, 32, 32 | 32 |

These are local fixture server-response times, not paint timings or field LCP/INP/CLS. `club-read-models.test.cjs` verifies deduplicated catalog reads and no archive histogram/summary fan-out. First-load JavaScript: Overview 96.5kB, Archive 98.5kB. No new infrastructure/chart/animation dependencies.

## Screenshots and limits

- [Overview dark](screenshots/overview-dark.png)
- [Filtered archive light](screenshots/archive-light.png)
- [320px week reviews dark](screenshots/week-mobile-dark.png)
- [Search error light](screenshots/search-error-light.png)

Screenshots contain **illustrative test data**, not real member activity. Not deployed. Real provider sign-in/linking remains unverified; existing platform status and Safe Browsing investigation still apply. No database migration or new architecture decision was needed.
