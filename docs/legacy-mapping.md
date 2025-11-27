# Legacy Schema Audit (current vs canonical)

All legacy tables, code, and bridge migrations have been removed. The repo now only contains the canonical schema defined in `agents/data-model.md`.

## Canonical schema (active)
- Users, LinkedAccounts (provider enum), Albums, Tracks, TrackFeatures.
- Club: Weeks, Nominations (genre/decade/country), Votes, Ratings.
- Listening: ListenEvents (with metadata/ingested_at).
- Social/analysis: TasteProfiles (per user + scope), Follows, Compatibility, UserRecommendations.
See `migrations/versions/0001_canonical_initial.py` for the authoritative create statements.

## Legacy status
- Removed: `sidetrack/common` package and all legacy models (artist/release/track int IDs, legacy listens, embeddings, mood tables, user_account/settings, etc.).
- Removed: transitional reboot tables (`core_user`, int `linked_account`, legacy week/vote/rating migrations) and bridge/backfill scripts.
- Removed: legacy services/tests under `services/` and `scripts/migrate_legacy.py`.

## Next steps
- Build migration scripts that assume a clean slate (only the canonical `0001_canonical_initial` revision).
- Reintroduce import pipelines against the canonical schema (Spotify/Last.fm, Discord bot sync) without legacy backfill paths.
