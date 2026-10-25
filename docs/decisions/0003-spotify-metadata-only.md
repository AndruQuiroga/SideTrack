# 0003: Spotify is metadata-only

- Status: accepted
- Date: 2026-10-25

## Context

On 2024-11-27 Spotify cut new apps off from audio features, audio analysis, recommendations, related artists and preview URLs. Since February 2026, Development Mode also caps an app at 5 authorized users and requires Premium. Recently-played returns only the last 50 tracks.

## Decision

Use Spotify only for album/track metadata, cover art and links, via client credentials. Listening history comes from Last.fm and ListenBrainz. Audio features come from our own models (ADR 0004 territory, analysis module).

## Consequences

- `track_features` columns shaped like Spotify audio features are retired.
- Spotify user OAuth and listen sync are dropped unless a new ADR revives them.
