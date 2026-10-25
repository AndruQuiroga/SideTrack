# 0008: Spec-driven development with OpenSpec

- Status: accepted
- Date: 2026-10-25

## Context

About 5k lines of agent task specs described features that didn't exist, and the fact that the ML models were mocked was lost. Work is done with both Codex and Claude Code.

## Decision

Use OpenSpec (`@fission-ai/openspec`, pinned as a dev dependency). Living specs in `openspec/specs/`, one folder per change in `openspec/changes/`. One shared `AGENTS.md`; `CLAUDE.md` imports it. `docs/STATUS.md` records what actually works. Spec scenarios need tests before a change is archived.

## Consequences

- `agents/*.md`, Copilot instructions and duplicate planning docs were deleted.
- Upgrading OpenSpec means bumping the dev dependency and rerunning `openspec update`.
