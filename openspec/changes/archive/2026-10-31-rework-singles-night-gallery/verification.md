# Singles Night gallery verification

Implementation inspected on 2026-10-28. The owner subsequently approved merge and
production deployment on 2026-10-29. Release `3d83256` is live; the
[rollout report](../../../deploy/SINGLES-GALLERY-2026-10-29.md) records its CI,
images, backup and signed-in browser/API checks. No historical records were
imported or modified.

## Acceptance matrix

| Behavior                                                                                                                   | Evidence                                                                                      |
| -------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Seven nights / 44 songs on the home page, source order, distinct session/song IDs, secondary detail links                  | `apps/web/tests/singles-gallery.test.cjs`; browser inspection of the hydrated real components |
| Eight-night batches, ninth summary lookahead, maximum three detail requests, stable output order                           | `apps/web/tests/singles-read-models.test.cjs`                                                 |
| Session-derived actor on every action; invalid offset/UUID and missing session make no API call                            | `apps/web/tests/singles-gallery-actions.test.cjs`                                             |
| Exact first/final means and counts; null empty mean; no join multiplication; deletion and repeated-song independence       | `services/api/tests/test_singles_nights.py`                                                   |
| Additive contract, existing fields preserved, actor headers retained                                                       | `tests/test_module_layout.py`; `packages/api-client/tests/act-as.test.cjs`                    |
| Precise source scores, compact summary, separate phases, omitted empty final section, explicit unrated/missing attribution | `apps/web/tests/singles-gallery.test.cjs`                                                     |
| Artwork failure and subsequent different-image recovery                                                                    | `apps/web/tests/album-art.test.cjs`; browser 404 fallback inspection                          |
| Append/retry, duplicate-click suppression, stable prior groups, auth loss and discarded late responses                     | `apps/web/tests/singles-gallery-interactions.test.cjs`                                        |
| Existing direct night URL and access states                                                                                | `apps/web/tests/singles-archive.test.cjs`                                                     |
| No browser service credentials                                                                                             | `apps/web/tests/authenticated-pages.test.cjs` (built client scan)                             |
| Responsive layout, keyboard disclosure, preserved expansion                                                                | Browser inspection below; committed screenshots                                               |

## Browser inspection

`apps/web/tests/render-singles-gallery-preview.cjs` renders and hydrates the real
gallery, card, image and store modules with local React dependencies and built CSS.
All identities, covers, ratings and action responses in this preview are synthetic
test fixtures. It exercises rendering and interaction; authenticated server/API
boundaries are verified by the action and Postgres tests above.

Inspected light and dark themes at 320, 390, 768 and 1440 px. Document scroll widths
were 305, 375, 753 and 1425 px respectively (the viewport reserves 15 px for its
vertical scrollbar), with no horizontal overflow. All 44 cards were in the DOM
without opening a night. Desktop uses three columns, intermediate widths two,
and 320 px one. Long titles wrap; a 755-character expanded review stays readable
at 320 px. Square artwork reserves its dimensions. Missing images and an actual
404 image show Artwork unavailable with song identity retained.

Enter on a focused native summary expanded and collapsed its disclosure. The
focused SUMMARY had a solid visible outline; accessibility state reported its
expanded/collapsed state. Loading older nights appended a third group (20 cards)
while retaining the previously open disclosure; the request counter was one.
The automated store test additionally proves duplicate clicks cannot issue a
second pending request. A subsequent mocked membership denial removed every card
and displayed the member-access notice. No browser console errors were recorded.

- [Narrow expanded card, light](evidence/mobile-expanded-light.png)
- [Desktop gallery, dark](evidence/desktop-dark.png)

## Checks

- Focused Postgres 16 + pgvector run: 7 Singles Night API tests and 13 module-layout
  tests passed (20 total). A disposable tmpfs database isolated from production
  was migrated by the test harness.
- Python Ruff lint and format checks passed; all seven import-linter contracts
  passed. Mypy passed for both changed source modules. The separately documented
  existing repository-wide type-check backlog is unchanged.
- API client TypeScript build and all 3 actor-header tests passed.
- Web ESLint, production build and all 77 web tests passed, including the built
  client credential guard. `/club/singles` measured 3.68 kB / 99.7 kB first-load JS
  in the production build.

No migration, provider lookup, new service, persistent browser cache or production
write is introduced. Rating aggregation uses already-loaded rows and the API test
asserts unchanged data/job/schedule counts and forbids provider calls. The reviewed
production rollout applied the additive API before web and verified all 44
summaries and unchanged protected records.
