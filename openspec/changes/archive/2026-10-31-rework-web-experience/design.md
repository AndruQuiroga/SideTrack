# Design

## Context

See `proposal.md` for motivation and scope; `research.md` records observations and sources. This is a proposed design, not a report of implemented behavior.

Observed implementation:
- `app/components/navbar.tsx`, `page-shell.tsx`, `ui.tsx`, and `globals.css` own shared chrome; individual routes also embed hardcoded decorative styles.
- `app/lib/server-api.ts` already represents access outcomes. Preserve session-derived actor identity and server-side credential handling.
- `app/lib/api/weeks.ts` lists only weeks with winners and hides optional rating failures as empty/undefined. `WeekDetail` exposes winner IDs, schedules, nominations, and aggregates, but no authoritative phase.
- Catalog album records provide identity and optional image URLs; pitches are prose. The existing week components assume the first nomination won.
- `/u/[id]/listening` already calls a supported recent-listens endpoint and paginates by 50; its profile backlink and full-history/Spotify copy are misleading.
- `oauth-buttons.tsx` currently hardcodes the post-sign-in destination to `/`. `settings/page.tsx` advertises capabilities incompatible with ADR 0003.

## Goals / Non-Goals

**Goals:** Make the release useful with existing endpoints, preserve direct links and access policies, isolate optional data failures, and allow aesthetic review across the same core journeys.

**Non-Goals:** Add domain behavior to compensate for missing backend features, interpret time as authorization, or ship mockup data. No new infrastructure or migrations. No production deployment in this change.

## Decisions

### 1. Shared application shell and explicit route responsibilities

Replace the floating navigation with a desktop sidebar and responsive mobile header/menu. Keep `PageShell` as the page-level composition point, backed by shared tokens and semantic primitives: Button, TextLink, StatusText, AlbumIdentity, Section, DataRow, AccessState, and Dialog. Use panels only for actual independent contexts; avoid making every section a Card.

| Entry | Route / behavior | Data |
| --- | --- | --- |
| Overview | `/` | Independent session-owned listens and club-context requests |
| Club | `/club/current`, with an Archive tab at `/club` | Existing list-weeks, week detail, catalog and ratings |
| Listening | `/listening` resolves owner from session; existing `/u/<id>/listening` retained | Existing recent-listens endpoint |
| Search | Shared accessible dialog | Existing server search proxy |
| Account | `/settings` | Existing linked-account flow |

`/discover`, `/feed`, `/compare`, `/blend`, and `/u/<id>` keep honest limitation screens and an onward link during this release. They do not invoke known absent or stubbed features. No dead links are added to the main shell.

Alternative: reskin every old feature equally. Rejected because this preserves the current mismatch between promise and functionality. Search remains a dialog because a catalogue-detail product is outside scope; metadata without a valid destination is noninteractive.

### 2. Journal selected after comparison of three visual studies

Owner decision, 2026-10-28: "I like the Journal one;". Journal is the selected implementation direction. Preserve its quiet sidebar, serif editorial titles, readable sans controls, restrained coral accents, small control radii, and artwork-led hierarchy. Console and Record store remain comparison references, not implementation alternatives awaiting a decision. No additional visual adjustments were requested.

The conversation preview offers the same overview, archive, week detail, history, and account content in three directions. It is explicitly illustrative, has no network requests or production mutations, and never enters `apps/`, `services/`, or `packages/`.

| Study | Layout and hierarchy | Proposed typography | Trade-off |
| --- | --- | --- | --- |
| Journal (selected) | Quiet sidebar, editorial album headline, open review column, compact archive | Georgia-style serif headlines and system sans controls | Selected balance; needs restrained heading scale |
| Console | Horizontal navigation, compact table-first archive and split detail | System sans plus monospace metadata | Efficient and precise; less cultural warmth |
| Record store | Typographic masthead, image-led archive, large cover/detail composition | Bold sans display and reading sans | Strong browsing identity; more scrolling |

Starting tokens for the selected Journal direction: charcoal canvas `#151615`, neutral raised surface `#1d1f1e`, warm text `#eeeee8`, secondary `#b1b5af`, border `#353835`, coral `#e59179`; equivalent light values in the preview. Selection is not a WCAG certification; measure and adjust actual text/control combinations while retaining the chosen visual direction. Radius scale 0/4/6/8px; circular avatars remain appropriate. Use 14-16px body text, clear 12-13px metadata, 28-40px page titles, and 44-56px editorial album headings only where space permits. No ambient gradients, glows, or ornamental live dots.

Default follows the user's existing preference where valid, otherwise system appearance; both supported themes use tokens. A final font choice can use system fonts without a network dependency. The existing theme button must change the full rendered theme; do not keep a cosmetic toggle.

### 3. Explicit web read models, retaining existing API contracts

Add server-only transformations rather than a new backend aggregation service. Keep per-section result states (`ok`, `empty`, `forbidden`, `unavailable`, `not-found`) and do not collapse failed rating or metadata requests into empty lists. Use existing API error handling for access boundaries.

For current context, request all weeks rather than `has_winner=true`. Order by descending week number, nulls last, then creation time descending and ID ascending. Label it Latest scheduled week, since a future week can be selected. Render stored schedule fields with UTC labels and wording such as Scheduled discussion. No synthesized phase or permission badge.

For winners, resolve `winner_album_id` via catalog reads. Match nomination metadata by album ID only where necessary. An admin override can point to an album without a nomination; resolve that album directly. Deduplicate album IDs per request and memoize shared server reads. Use fixed-size artwork regions with meaningful alt text; missing or failed images show Artwork unavailable. Preserve album text when image loading fails.

Lists use existing week aggregates. Fetch detailed reviews and histogram only for a selected week, avoiding today's summary fan-out across the archive. A missing distribution remains missing; aggregate counts do not determine histogram shape. Bound review excerpts and provide a local Show more for full text rather than silently omitting all reviews beyond six.

Alternative: introduce a richer week API now. Rejected because existing endpoint fields suffice and no model changes are required. Record latency during implementation; if catalog joins prove inadequate, propose a separate backend read-model change.

### 4. URL-owned archive state and stable labels

Whitelist `q`, `tag`, `sort=newest|rating`, and `view=grid|list`. Omit defaults, constrain query length, and normalize unknown values. Keep search/filter changes local to the already authorized collection and synchronize the URL with history replacement. Build detail links with an encoded same-origin archive return path; browser Back and explicit Back to archive restore the same state.

Search album title, artist, week label, and available nomination tags. Explain that a metadata filter matches nomination metadata, not an inferred winner genre. Rating sort places unrated entries last, with date and ID tie-breakers. Latest winner is selected from the unfiltered winners by discussion time or creation time, independently of sort. Display only one selected tag in this release.

Alternative: local React state only. Rejected because refresh, links, and back navigation would lose context.

### 5. Session-safe sign-in and private listening

Thread a normalized same-origin relative return path from AccessState to `/login` and `signIn`. Reject external schemes, protocol-relative paths, backslashes, and malformed encodings; default to `/`. Sign-in remains Discord-only. Do not bypass the documented provider/browser verification limitation.

`/listening` uses the session ID and the existing recent-listens adapter, never profile analytics. UTC day grouping and displayed timestamps use the same timezone, visibly labeled. Retain 50-row pagination. Do not fabricate last-sync or import progress when unavailable. Owner-only connection actions remain on Account; another user's history never exposes their linked accounts.

Alternative: make new profiles a prerequisite. Rejected because it expands backend scope and blocks a working history endpoint.

### 6. Accurate connection and unsupported-feature presentation

Discord is identity and club eligibility remains separate. Last.fm offers only the existing supported connection behavior, with its real linked account name and availability. Spotify may have an informational metadata-only row; no personal Connect Spotify control. Legacy records do not imply active tracking. Do not add disconnect, import-status, or manual-sync actions unless existing supported contracts provide them; unavailable actions are explained without pretending success.

Use persistent inline errors for failed connect attempts and a retry that actually restarts the existing request. Every shared layout handles signed-out, forbidden, empty, no matches, and unavailable states without invented values. Existing `web/data-honesty` and `web/authenticated-pages` remain in force.

### 7. Verification is behavioral and visual

Keep current Node/React-rendered tests and add focused tests under `apps/web/tests`. Suggested files in `tasks.md` are implementation targets, not present evidence. Use browser checks against an isolated local server with fixtures confined to tests, never production fallbacks. Validate signed-in/member/non-member states, narrow screens, keyboard focus, color contrast, artwork failure, and real navigation.

Run web build before tests because existing bundle-boundary tests require `.next/static`. Run web lint, tests, and build; TypeScript changes may also require workspace lint/build. No Python changes are planned. Track LCP <=2.5s, INP <=200ms, CLS <=0.1 as field targets, not claims proven by a local screenshot. Keep loading placeholders dimensionally stable and avoid heavyweight chart/animation dependencies.

## Risks / Trade-offs

- [Missing authoritative club phase] -> Show stored schedules and Discord destinations, not claimed phase permissions.
- [Sparse data makes artwork-led layouts look empty] -> Review real empty/partial states alongside illustrative filled screens.
- [Current callback verification is unresolved] -> Preserve access/error behavior; test local return normalization and report live auth separately.
- [Catalog joins add latency] -> Deduplicate IDs, reuse request-scoped reads, avoid per-week histogram requests, measure before adding infrastructure.
- [Unsupported routes feel reduced] -> Preserve URLs and explain exact limitations; capability work remains separately scoped.
- [Design study mistaken for real club data] -> Label it illustrative in every variant and keep its data outside application source.
- [Existing data-honesty defects survive visual migration] -> Complete the separate fix change first and retain its behavioral tests when replacing components.

## Migration Plan

1. Completed: the owner selected Journal after reviewing the three visual studies. The decision above is the implementation baseline.
2. Apply `fix-web-data-honesty-regressions` separately before releasing the redesign.
3. Add shared tokens and shell, then migrate overview, club pages, history, Account, sign-in, and limitation/error routes in small reviewable steps. Preserve supported URLs throughout.
4. Run the acceptance matrix and compare the three core screens at desktop and mobile sizes. Update generated status from YAML only after evidence exists.
5. Deployment is a separately authorized step. No database migration is needed. Roll back with the previous web image; preserve the independent data-honesty fix in any rollback build.

## Open Questions

- Final verification uses Georgia/system font fallbacks and strengthens control boundaries to `#82877b` light and `#646b62` dark. Actual theme contrast tests pass; implementation evidence is in `verification.md`.
