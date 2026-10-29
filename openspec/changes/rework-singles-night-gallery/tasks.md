# Tasks

## 1. Honest song summaries

- [x] 1.1 Add additive per-song `rating_summary.first/final` count/average read fields computed from stored ratings; verify precise means, empty phases, independent phases, multiple-submitter/artwork joins, repeated songs and deleted-user contributions in `services/api/tests/test_singles_nights.py`, including unchanged 200/403/401 access and no writes/provider calls.
- [x] 1.2 Regenerate the API/client contract and document per-phase semantics; verify `tests/test_module_layout.py` retains all previous fields, API-client build/actor tests pass and API documentation names empty-phase null averages.

## 2. Home-page data loading

- [x] 2.1 Implement the server-only eight-night gallery batch loader with one lookahead summary and at most three concurrent detail requests; prove seven-night/44-song initial loading, stable order, empty archives, bounded concurrency, partial failures and unchanged identities in `apps/web/tests/singles-read-models.test.cjs`.
- [x] 2.2 Add session-authorized server actions for older batches and group retries; prove fresh actor derivation, invalid offset/UUID rejection, no caller-supplied identity/path, missing-session no-call behavior and access-loss outcomes in `apps/web/tests/singles-gallery-actions.test.cjs`, and document the request/access boundary alongside the gallery read model.

## 3. Gallery presentation and interaction

- [x] 3.1 Replace the Singles Night home-page summary tiles with newest-first night headings and artwork-led song cards; prove all seven fixture nights and 44 cards appear without night navigation, readable missing art/attribution, unchanged submission order, distinct repeated picks and secondary direct links in `apps/web/tests/singles-gallery.test.cjs`.
- [x] 3.2 Add accessible inline impressions with API-supplied compact summaries, exact individual ratings/reviews and conditional final sections; prove expansion/collapse, unrated versus zero, phase separation, long reviews and missing artwork behavior in `apps/web/tests/singles-gallery.test.cjs` and `album-art.test.cjs`.
- [x] 3.3 Append older batches and retry failed groups in place while preserving prior cards/disclosures; prove duplicate-click suppression, stable IDs, preserved expansion, partial retry and global access changes in `apps/web/tests/singles-gallery-interactions.test.cjs`. Keep night detail URLs working through shared card presentation and retain `singles-archive.test.cjs` direct-link/access coverage.
- [x] 3.4 Extend the synthetic visual preview to the actual multi-night home page; verify light/dark layouts at 320/390/768/1440 widths, keyboard focus/disclosure labels, image load failure, readable metadata and no horizontal overflow. Record inspection evidence in this change's `verification.md`; keep synthetic fixtures under tests only.

## 4. Integration and documentation

- [x] 4.1 Run focused API/Postgres tests, Python lint/type/import checks for changed code, API-client tests/build, web lint/build/all tests including the browser credential guard, and strict OpenSpec validation; retain command results and verify there are no new migrations, historical writes or cross-user caches.
- [x] 4.2 Update `docs/status.yaml`, regenerate `docs/STATUS.md` and document the implemented home-page behavior and measured request bounds with real test/visual evidence; verify `scripts/gen_status.py --check`, tracked evidence paths and the full acceptance matrix before marking the UI work complete.

## Workflow follow-up

- Review the implemented home gallery before a separate production rollout. Deploy the additive API contract before the web image; retain member access and compatible existing services.
- Archive only after the owner requests it and the spec scenarios have verification evidence.
