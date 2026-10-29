# Artwork recovery

Artwork is optional metadata, independent of club ratings and import evidence.
Album reads include nullable `artwork_source_url`; Singles Night song reads include
nullable `cover_url` and `artwork_source_url`. Existing member and server-session
authorization remains in effect. Missing or failed images display **Artwork unavailable**.
Provider images link back to the relevant music entity; no provider iframe, audio,
credential or private recovery evidence is sent to the browser.

## Operator workflow

Use `uv run --frozen --extra api python -m sidetrack.artwork` locally, or
`python -m sidetrack.artwork` inside the published API image. Keep all input/output
files in a protected directory outside Git. Commands refuse to overwrite reports.

1. `inventory --output /private/inventory.json` reads target identities and cover state.
2. `preview --inventory /private/inventory.json --review /private/review.json --output /private/preview.json`
   performs provider metadata and bounded artwork lookups, without archive writes.
3. `check --plan /private/preview.json --output /private/checked.json` binds ready
   candidates to the current database. Existing, unavailable, unresolved and conflicting
   entries are not written. Review the exact digest and coverage privately.
4. `apply --plan /private/checked.json --expected-digest CHECKED_DIGEST` atomically
   rechecks and fills only still-missing artwork.
5. `verify --plan /private/checked.json --output /private/verification.json` reports
   mismatches and erased targets. An identical apply is a verification/no-op.
6. `reverse --plan /private/checked.json --expected-digest CHECKED_DIGEST` removes
   only matching recovered artwork; changed or deleted targets require manual review.

Inventory/check/verify open read-only database transactions. Apply/reverse use
serializable transactions, an advisory lock and target row locks. Discovery is
performed separately so slow provider requests do not hold write locks.

## Provider identities and prerequisites

Spotify Web API discovery uses existing client credentials configured by environment
or Docker secrets. Do not print or paste them. No Spotify user OAuth is required.
Only exact album/track links or a unique normalized artist/title/edition match are
accepted. Metadata identity conflicts are reported, never silently substituted.

A private review is keyed by `album:TARGET_UUID` or `song:TARGET_UUID`. It can select
`spotify_url` or a reviewed `musicbrainz_id`. For a credential-free exact Spotify
lookup, include `verified_identity` with `url`, `title`, `artist_name`, `reason` and
an `evidence_digest` SHA-256 of independently checked identity evidence. The URL must
be canonical and the artist/title must match the selected target. Spotify oEmbed
must independently return the matching title and an image. A thumbnail alone cannot
establish artist identity. Review entries cannot supply arbitrary image URLs.

MusicBrainz fallback validates an explicitly reviewed release-group identity through
the existing shared pacing guard, then checks its Cover Art Archive front image.
Bulk resolution must continue to follow ADR 0005. Failed providers remain explicit
gaps; ambiguous editions are not guessed.

Images must use approved HTTPS provider/CDN hosts. Each redirect is validated before
following; private-network addresses, credentials, unsupported formats and oversized
responses are rejected. Duplicate requests are cached within a preview. No Discord
attachments or audio are fetched. Live provider availability is separate from the
synthetic transport tests.

References: [Spotify track metadata](https://developer.spotify.com/documentation/web-api/reference/get-track),
[Spotify oEmbed](https://developer.spotify.com/documentation/embeds/reference/oembed),
[Cover Art Archive API](https://musicbrainz.org/doc/Cover_Art_Archive/API).

## Historical compatibility and recovery boundary

Album cover updates use catalog-owned operations. Song artwork lives in a separate
club-owned row, so the original song columns and durable history hashes do not change.
No original batch/source digest is rewritten. Recovery receipts retain structured
target/provider/evidence information, never accounts or source conversations.
Deleting a song/album cascades its artwork. Retrying a receipt never recreates an
erased target. A reversed receipt cannot be used to reapply artwork automatically.

Artwork reversal preserves history, accounts and subsequent activity. A full database
restore is separate disaster recovery requiring review of newer data. See the
deployment runbook for backup, rehearsal and rollout requirements.
