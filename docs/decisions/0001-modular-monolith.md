# 0001: Modular monolith

- Status: accepted
- Date: 2026-10-25

## Context

The repo had grown into separate API, worker, extraction and bot services that shared one database and one god token, with no enforced boundaries. Workload: one club and a handful of users.

## Decision

One Python package (`sidetrack/`) with five modules: `identity`, `catalog`, `listening`, `club`, `analysis`. Each module owns its tables and exposes public functions; no module writes another's tables. Boundaries are enforced with import-linter in CI. The package runs as a few processes (API, worker, GPU worker, bot), all importing the same code. The Next.js web app stays separate and talks only to the API.

## Consequences

- No HTTP hop or shared token between internal processes.
- Moving existing code into modules is Phase 1 of the refactor.
- A module split into a service later needs a new ADR.
