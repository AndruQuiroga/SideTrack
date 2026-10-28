# Tasks

Journal is the selected and implemented direction. Evidence for completed tasks is recorded in `verification.md` and the named test files below.

## 1. Visual baseline and prerequisite

- [x] 1.1 Record the owner's chosen direction and agreed adjustments in `design.md`. Evidence: owner feedback on 2026-10-28, "I like the Journal one;", after the comparable overview/archive/week-detail studies; Journal selected, no additional adjustments requested. Production visual and accessibility verification remains in 7.2.
- [x] 1.2 Complete the separately scoped `fix-web-data-honesty-regressions` before release; verify its `apps/web/tests/club-data-honesty.test.cjs` passes and preserve it during component migration.

## 2. Shell, navigation, and sign-in

- [x] 2.1 Implement selected theme tokens and semantic shared controls in the existing web styling/components; add rendered hierarchy coverage in `apps/web/tests/interface-presentation.test.cjs` and document tokens in `apps/web/README.md`. Verify shared routes have no decorative gradient chrome, fake live dots, or emoji feature tiles.
- [x] 2.2 Replace global navigation with the responsive shell and labeled mobile menu; add `apps/web/tests/application-navigation.test.cjs` for destinations and active state, plus a keyboard/mobile browser check at 320px proving destination selection closes the menu.
- [x] 2.3 Preserve safe same-origin sign-in destinations through AccessNotice, login, and OAuth buttons; extend existing `apps/web/tests/discord-sign-in.test.cjs` for filtered archive return, external URLs, protocol-relative paths, backslashes, and malformed encodings. Verify OAuth callback receives the normalized relative path.
- [x] 2.4 Implement independent overview sections and honest legacy-route limitation pages; test signed-out no-fetch behavior, partial section failure, preserved week links, legacy blend no-generation, and unsupported navigation removal in `application-navigation.test.cjs` and existing `authenticated-pages.test.cjs`.

## 3. Club read models and current context

- [x] 3.1 Introduce server-only latest-week and winner/catalog transformations using existing endpoints; add `apps/web/tests/club-read-models.test.cjs` proving future-week selection, null-number/tie ordering, a winner outside first nomination, an admin override without a nomination, and catalog failure. Verify duplicate album IDs produce one catalog read per request.
- [x] 3.2 Implement `/club/current` and overview album/schedule composition with existing Discord destinations; add `apps/web/tests/club-browsing.test.cjs` for empty weeks, explicit UTC schedules, no inferred voting permission, valid/missing thread destinations, and no web participation controls. Document current versus archive routes in `apps/web/README.md`.

## 4. Archive and week detail

- [x] 4.1 Add URL-owned archive query, tag, sort, and view state; test normalization, share/reload, no-match reset, rated/unrated sorting, independent latest-winner selection, and detail/back restoration in `apps/web/tests/club-archive-state.test.cjs` with a browser round-trip check.
- [x] 4.2 Recompose archive grid/list and week detail around real album identity, artwork, schedules, ratings, reviews, and nominations; extend `club-browsing.test.cjs` for missing/failed artwork, section order, optional-request failure versus empty ratings, histogram absence, and readable full reviews.
- [x] 4.3 Replace archive per-week histogram/summary fan-out with existing aggregate fields and request detail only when needed; verify request counts in `club-read-models.test.cjs`, and record observed local navigation latency in the implementation verification notes.

## 5. Listening and account

- [x] 5.1 Add the session-owned `/listening` entry and rework the existing history route independently of profile endpoints; add `apps/web/tests/listening-history.test.cjs` for session actor, private-other-user denial, UTC midnight grouping, invalid page input, 50-row pagination, empty records, unavailable API, and absent coverage metadata. Document stored-history coverage and UTC display.
- [x] 5.2 Recompose Account and supported connection controls with accurate Discord/Last.fm/Spotify descriptions and inline failure feedback; extend existing `apps/web/tests/connections.test.cjs` for lookup failure, empty/supplied accounts, legacy Spotify records without a connect action, and absence of unsupported progress/now-playing promises.

## 6. Search and shared state completion

- [x] 6.1 Rework the existing search dialog with accessible naming, focus containment/restoration, Escape dismissal, and explicit result destinations; add `apps/web/tests/search-dialog.test.cjs` for no-result/error rendering and metadata-only records, plus a browser keyboard test for focus behavior.
- [x] 6.2 Migrate remaining sign-in, loading, error, not-found, and limitation screens; test the full access-state matrix in `interface-presentation.test.cjs` and existing `authenticated-pages.test.cjs`. Document retry semantics and ensure no failed optional request is converted into an empty success.

## 7. Integration and evidence

- [x] 7.1 Run `pnpm --filter @sidetrack/web lint`, `pnpm --filter @sidetrack/web build`, then `pnpm --filter @sidetrack/web test`; run required workspace `pnpm lint` and `pnpm build` for the final TypeScript integration. Preserve existing built-bundle credential boundary and data-honesty tests. Record failures accurately rather than marking them passed.
- [x] 7.2 Verify desktop and 320/390px layouts in both themes, contrast, touch targets, keyboard-only navigation, reduced motion, image failure, and signed-out/non-member/empty/error states; record screenshots and results in `verification.md` with each spec scenario mapped to a named passing test or explicit browser check. Record performance measurements as local evidence, not field-percentile claims.
- [x] 7.3 Update `docs/status.yaml` only for behavior with actual evidence, run `uv run --frozen --extra dev python scripts/gen_status.py`, and verify the generated status is current with `test_gen_status.py`; update an ADR only if implementation introduces a new architectural decision. Verify both changes with `pnpm exec openspec validate <change-name> --strict`.

## Workflow follow-up

- Review completed implementation before any separately authorized deployment.
- Archive after scenario evidence and the project's review requirements are satisfied.
