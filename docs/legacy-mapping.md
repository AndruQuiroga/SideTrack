# Legacy Schema Audit (Current vs Canonical)

This report inventories the current SQLAlchemy models/migrations and compares them with the canonical domain model in `agents/data-model.md`. Use it to guide Phase 2 migrations.

## Current tables (models + migrations)

- **artist / release / track**: legacy music catalog tables using integer primary keys and optional MusicBrainz IDs. Track includes ISRC, Spotify ID, duration, local path, fingerprint, and pgvector embeddings. Constraints added for embeddings/features uniqueness and IVFFlat index on `track.embeddings`.
- **listen**: per-play log with `user_id` (string), `track_id` FK, `played_at`, and `source`. Indexes on `user_id`, `played_at`, and `track_id`.
- **features / embeddings**: JSON audio features and generic embedding storage with `dataset_version`, model identifiers, and uniqueness constraints.
- **track_features / track_embeddings / track_scores**: more structured per-track features, vector embeddings, and metric scores (composite PKs include `dataset_version`/`model`).
- **mood_scores / mood_agg_week**: mood metrics per track and aggregated per user/week/axis.
- **labels_user**: user-provided labels per track (axis/value).
- **lastfm_tags / mb_tag / mb_label / mb_recording**: cached tag/label metadata from Last.fm and MusicBrainz (MB tag/label/recording tables exist in models but not covered by current migrations).
- **graph_edges**: edges between tracks with weight and kind, unique per (src, dst, kind).
- **user_account**: auth table with password hash, optional token hash, role (default `user`), and timestamps.
- **user_settings**: per-user external account config (ListenBrainz, Last.fm session key stored as `lastfm_api_key`, Spotify tokens/usernames, GPU/stems/excerpts flags).
- **insight_events**: timestamped user events with type, summary, optional details JSON, and severity.

## Alignment against canonical model (`agents/data-model.md`)

| Canonical entity | Current status | Gaps / differences |
| --- | --- | --- |
| User | Only `user_account` (string PK, password/token/role) and `user_settings` (provider tokens) exist; no UUID `users` table or `display_name`/`handle` fields. | Add canonical `users` table; map legacy `user_id` strings; migrate auth/settings appropriately. |
| LinkedAccount | Missing; provider details live in `user_settings` columns. | Introduce `linked_accounts` with provider enum + identifiers/tokens; backfill from `user_settings`. |
| Album / Track | Legacy `release`/`track`/`artist` tables differ from canonical `albums`/`tracks` (UUID PKs, album-centric). | Decide mapping of `release`→`albums`; add canonical album/track tables alongside or migrate; normalize artist fields. |
| Week | Missing entirely. | Add `weeks` table with scheduling + Discord thread IDs. |
| Nomination | Missing. | Add `nominations` linked to `weeks`/`users`/`albums` with pitch + tags. |
| Vote | Missing. | Add `votes` with unique (week, user, rank) + nomination FK. |
| Rating | Missing. | Add `ratings` with (week, user) uniqueness, album FK, favorite track, review. |
| ListenEvent | `listen` table partially matches but uses string `user_id` and integer track IDs; lacks source enum/UUIDs. | Add canonical `listen_events` with UUIDs, migrate data from `listen`. |
| TrackFeatures | Two overlapping systems (`features` JSON + `track_features` JSONB). Canonical expects lighter-weight audio features per track. | Decide canonical structure; likely map to `track_features` (drop legacy `features`?) with UUID FKs. |
| TasteProfile | Missing. | Add `taste_profiles` JSONB aggregates per user. |
| Follow | Missing. | Add `follows` with unique follower/followee. |
| Compatibility | Missing. | Add compatibility table keyed by user pairs. |
| UserRecommendations | Missing. | Add `user_recommendations` table for cached suggestions. |

## Phase 2 migration notes

- Introduce canonical user/social tables (users, linked_accounts, follows, compatibility, taste_profiles, user_recommendations) and plan data backfill from `user_account`/`user_settings`.
- Add club tables (weeks, nominations, votes, ratings) per canonical schema; no legacy equivalents exist.
- Stand up canonical album/track tables (UUIDs) alongside legacy `release`/`track` and design mapping/duplication strategy.
- Normalize listening + features: create `listen_events` with UUID FKs and migrate from `listen`; reconcile `features` vs `track_features` and align with canonical `TrackFeatures` fields.
- Review metadata caches (`mb_tag`, `mb_label`, `mb_recording`) since models lack migrations—decide whether to keep or recreate under new schema.
