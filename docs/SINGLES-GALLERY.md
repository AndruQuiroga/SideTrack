# Singles Night gallery

The home-page implementation is developed under `rework-singles-night-gallery`.
Release `3d83256` is live following the owner-approved
[2026-10-29 rollout](../deploy/SINGLES-GALLERY-2026-10-29.md).

`/club/singles` renders songs grouped by night, newest first. Initial loading uses
one index request for nine summaries: eight nights plus one lookahead. At most
three detail requests run concurrently. Seven current nights fit the first batch;
older nights append without opening individual night pages. Failed groups retain
their heading and a retry; an empty archive is distinct from an outage.

Every older/retry server action re-reads the signed-in session. Inputs are limited
to a nonnegative integer offset or a session UUID. Actors, API paths and credentials
never come from the browser. Results are held only in the mounted gallery's memory,
with stable session/song keys; authorization failures clear visible gallery data.

## Rating contract

Each SinglesSongRead adds `rating_summary.first` and `rating_summary.final`, each
containing `count` and `average`. A phase with no ratings returns count 0 and average
null. Means are computed in the API from stored ratings for the exact song/phase;
submission/artwork joins do not multiply scores. Counts represent rating records,
not inferred unique listeners or ballots. Existing individual score precision is
unchanged. The compact summary formats the API mean to one decimal for display.

Native details/summary disclosures expose individual listener scores and reviews
inline. Final sections appear only when final ratings exist. Missing first ratings
read Not rated yet; missing API summaries read Rating summary unavailable.
Artwork remains optional, keeps its provider attribution link and reserves square
space before loading. No music playback, provider fetches or historical writes
occur in this gallery.

## Verification and release

All 77 web tests, 20 focused API/contract tests on isolated Postgres, the client
build and three client tests pass. Python lint, format, changed-module type checks
and all seven import contracts pass. Browser inspection covers the real hydrated
components in both themes at 320, 390, 768 and 1440 px, including long reviews,
keyboard disclosure, failed images, preserved expansion and access loss.

The [acceptance matrix](../openspec/changes/archive/2026-10-31-rework-singles-night-gallery/verification.md)
records the evidence and synthetic preview command. Production verification also
confirmed all seven nights/44 cards, inline impressions and direct night links in
the signed-in browser. The additive API deployed before web; schema 0012 and all
fourteen audited history/account table fingerprints were preserved.
