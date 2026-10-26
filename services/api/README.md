# API Service

The implementation lives in the canonical `sidetrack` package. This directory
retains compatibility imports, API tests, and Docker/startup files. See
[module boundaries](../../docs/MODULES.md) for ownership and runtime commands.

## Canonical schema snapshot

- `users` + `linked_accounts` for identity and provider links (Discord, Spotify, Last.fm, etc.).
- Music catalog: `albums`, `tracks`, `track_features`.
- Club: `weeks`, `nominations`, `votes`, `ratings`.
- Listening: `listen_events`.
- Social/analysis: `taste_profiles`, `follows`, `compatibility`, `user_recommendations`.
