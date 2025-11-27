# API Service

This directory scaffolds the Sidetrack API service, which exposes the backend data models and endpoints for the bot, web app, and worker processes.

## Canonical schema snapshot
- `users` + `linked_accounts` for identity and provider links (Discord, Spotify, Last.fm, etc.).
- Music catalog: `albums`, `tracks`, `track_features`.
- Club: `weeks`, `nominations`, `votes`, `ratings`.
- Listening: `listen_events`.
- Social/analysis: `taste_profiles`, `follows`, `compatibility`, `user_recommendations`.
