# Design

## Context

See proposal.md for motivation and the two delta specs for the behavior contract. Owner decision on 2026-10-28: prefer the first Song gallery example, applied to the Singles Night home page; do not require opening each night to see its songs. The chosen Journal visual direction in `rework-web-experience/design.md` remains the baseline.

Observed: `/club/singles` fetches summary records and renders night links. Full songs/artwork/submissions/ratings are returned only by `GET /club/singles-nights/{id}` and displayed in `SinglesDetail`. The existing loader walks all index pages, but does not hydrate songs. Session listing already supports limit/offset and descending date/week/ID ordering. Stored data currently has seven nights, 44 songs and 38 recovered song covers (`docs/STATUS.md`), with no historical final ratings.

Observed: `web/data-honesty` requires displayed scores to come from API results. The existing detail API returns individual scores but no per-song mean/count summary. `server-api.ts` already derives actor identity from server sessions and represents access outcomes. Shared AlbumArt handles fixed-square images and failed-image fallback.

## Goals / Non-Goals

**Goals:** Make the home page useful on first load; give songs equal visual weight; keep ratings and provenance available without making them the dominant content; bound each server request batch; preserve access, history, and direct links.

**Non-Goals:** Treat a selected song or high mean as an official winner; introduce playback, public sharing, database changes, filters, a new global shell, provider calls during rendering or an artwork backfill. Deployment is a later release action after implementation review.

## Decisions

### 1. Home page is a feed of night groups and song galleries

Keep `/club/singles` as the main route and existing Club tabs. Use a restrained Singles Night page heading and a brief music-focused description; avoid a large invented statistics dashboard or a single-night hero that hides older picks. Each visible night has its number/date, actual song count, a subtle original Discord source link, and its full song grid below. Groups render newest first using API order; unknown dates remain explicitly unavailable. Song order remains the API's stored submission order.

Cards use large square covers, title/artist, submitter and one compact first-listen score/count line. Start with three columns in the normal desktop content width, two on medium/narrow widths where text remains readable, and one below the comfortable two-card minimum; verify at 320, 390, 768 and 1440 pixels. Use existing Journal tokens, readable typography and restrained coral for score/action emphasis. Do not wrap the whole feed in another dashboard panel.

Alternative: a night picker or clickable session tile grid. Rejected because it preserves the extra step the owner explicitly wants removed. Alternative: one large featured song. Not selected by the owner and would subordinate the rest of the songs.

### 2. Expand song impressions inline

Use a native `details`/`summary` disclosure per card, exposing the browser’s expanded state and keyboard button semantics with its associated panel. Show concise first-listen summary text such as `3.8 / 5 · 2 first-listen ratings`, using the API mean formatted to one decimal only for this summary. Do not change individual precision. The panel lists listener names, original scores and reviews. Final ratings receive a separate labeled subsection only when count is nonzero; never render an empty final-rating column for every historical card. Empty first-listen phases read Not rated yet.

Keep identity and controls visible when artwork fails. Multiple submitters retain their names, and missing/deleted attribution is labeled unavailable. Music/provider and Discord links live in the expanded details or an unobtrusive card action row. The disclosure button and external links are separate interactive targets, without nested links/buttons. Cover attribution remains linked to its provider. No fake play controls, audio embeds or automatic playback.

Expansion state is keyed by session ID plus song ID. Repeated music across nights remains separate. Existing `/club/singles/[id]` links remain secondary and reuse the same song-card/disclosure presentation so old bookmarks keep working. Expanding a song never requires that detail route.

### 3. Bound first render and incremental older loads

Introduce a server-only gallery batch loader that requests nine index summaries at an offset: eight displayed nights and one lookahead to determine whether older nights exist. Hydrate the displayed summaries using at most three concurrent existing detail calls. Initial render is server-rendered with real song cards; all seven current nights and all 44 songs fit the first batch. Do not eagerly hydrate the entire future archive, or require a client request before showing initial songs.

A narrowly scoped Next.js server action appends the next eight-night batch when Show older nights is activated. It accepts only a validated nonnegative integer offset; batch size/concurrency remain server constants. The action re-reads `sessionUserId()` for every request, constructs the API actor server-side and returns only authorized read data. It accepts no actor ID, arbitrary API path or provider URL. The browser holds rendered data and interaction state, never credentials or the internal API client.

Client composition merges groups by stable session IDs, preserves existing expanded panels and disables duplicate in-flight requests. Offset advances by the summaries consumed, including a temporarily unavailable night, so one failed detail does not stall older discovery. A retry for that specific group uses a UUID-validated session ID and fresh server authorization; it cannot select an arbitrary endpoint. Transient errors retain earlier groups and offer a functional retry.

Alternative: a new backend gallery service or cache. Existing index/detail endpoints are sufficient for eight nights per batch; a new service or persistence layer is unnecessary. Alternative: fetch all details without bounds. Rejected because archive growth should not turn a home-page view into unbounded concurrent requests.

### 4. Add honest per-phase summaries to the existing API read model

Add `rating_summary` to SinglesSongRead, containing `first` and `final` objects with `count: int` and `average: float | null`. Compute both from the already loaded individual rating collection for the exact song/session, with no submission/artwork join multiplication. Return the arithmetic mean without rounding away source precision; format the compact card display separately. Existing individual rating fields remain unchanged. No schema migration or stored aggregates are needed.

Update the generated API/client contract additively and test old fields remain unchanged. Member/bot reads retain their existing authorization. The web displays only API-returned summary values and labels each phase; it does not derive winners or conflate rating counts with unique listener counts.

Alternative: compute new displayed means in the client from raw ratings. Rejected because the established data-honesty contract requires API-returned scores and a single authoritative summary makes phase semantics testable.

### 5. Distinguish data absence, partial outages and access changes

Represent each hydrated group as ok, unavailable or not-found. Keep successful groups if one detail read fails; show the summary heading and a localized Songs unavailable retry state, not an empty gallery or invented cards. A session deleted between listing and hydration gets an honest unavailable/removed message and a refresh path. Do not claim a failed group's songs are fully loaded based solely on its index count.

Absent server sessions show sign-in without API calls. A 401/403 during any hydration/action becomes the appropriate global access outcome, suppressing additional private results and clearing visible gallery data in the client composition when the access outcome changes. Reuse existing access classification rather than expanding auth behavior in a UI task. An empty authorized index is distinct from an outage. Do not cache actor-specific responses across users or use persistent browser storage for private gallery data.

### 6. Verify the chosen home-page composition

Use synthetic multi-night fixtures outside production code. Cover seven nights/44 songs, older batches, repeated songs, image failures, long titles, multi-line reviews, multiple/deleted submitters, no ratings, both phases and one unavailable night. Test request bounds, retries, deduplication, fresh server-session actors and preserved expansion state. Retain existing member/direct-link tests and the browser credential-bundle guard.

Inspect the home page in light and dark themes, with desktop and narrow-screen keyboard/touch interactions. Record contrast, visible focus, disclosure semantics, natural image ratios and no horizontal overflow. Keep loaded cards stable while older groups append; no virtualization or animation library is needed for the initial 44 songs.

## Risks / Trade-offs

- [Detail calls add latency] → Fixed eight-night batches, concurrency three, one lookahead index request and no provider calls; measure initial request counts and page latency during implementation.
- [Offset pagination overlaps during new inserts] → Stable IDs prevent duplicate groups; preserve already loaded data and provide refresh for a current snapshot. Do not promise a transactionally frozen archive.
- [Sparse/missing artwork weakens the gallery] → Reserve identical cover regions with explicit unavailable text, retaining equally readable music identity.
- [Ratings look like an official competition result] → Label first-listen means/counts and keep submission order; no winner labels or leaderboard.
- [Expanded long reviews create uneven rows] → Let cards grow naturally without truncating identity/reviews or overlaying adjacent cards; compare real narrow-width layouts before release.
- [Access lost during an incremental action] → Reauthorize every request and map the result to a global access state without leaking credentials or additional records.

## Migration Plan

1. Implement/test additive API summaries and regenerate the client/contract.
2. Add bounded server-only batch loading and authorized incremental/retry actions.
3. Replace the home-page summary tile list with grouped song galleries and shared inline impressions; retain direct night links.
4. Run API/Postgres, web behavior/build/lint, credential boundary and visual checks; update generated status only with actual evidence.
5. Review the implemented home page before any production rollout. A later release deploys the compatible API before web; reverting the web image restores the old list without data migration or historical writes.
