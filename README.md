# Sidetrack

A Discord album club plus audio-first listening intelligence, self-hosted on a homelab.

The project is mid-refactor. **What works today is in [docs/STATUS.md](docs/STATUS.md)**; this README doesn't describe planned features.

- **Club:** a weekly Discord cycle (nominate → ranked vote → listen → rate) with a public web archive.
- **Listening:** import Last.fm / ListenBrainz history and resolve it against MusicBrainz.
- **Analysis (planned):** audio embeddings and labels from local models; see [ADR 0004](docs/decisions/0004-audio-analysis-benchmark-first.md).

## Docs

- [Status](docs/STATUS.md): what actually works
- [Decisions](docs/decisions/): architecture decisions
- [Module boundaries](docs/MODULES.md): Python ownership, imports and startup
- [Refactor progress](docs/ROADMAP.md): phases and deferred operational checks
- [Specs](openspec/specs/) and [changes in flight](openspec/changes/)
- [AGENTS.md](AGENTS.md): working rules and commands, for agents and humans alike
- [Bot user guide](apps/bot/USER_GUIDE.md)

## Quick start (local)

```bash
cp .env.example .env
docker compose up --build
```

## License

Private project; no license granted.
