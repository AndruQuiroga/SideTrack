# Refactor progress

This is a phase index, not a claim that planned capabilities work. See STATUS.md
for observed behavior and openspec/changes/ for implementation tracking.

## Phase 0: honest baseline and deployment preparation

PRs #280–#282 delivered OpenSpec, credential hardening, runtime secrets and health
checks, deployment artifacts, removal of invented page data, Postgres migration
tests, and a generated status report. The follow-up
`remove-fabricated-connection-status` removes an overlooked default linked account
and distinguishes unavailable account data from an empty successful lookup.

Two operational checks remain explicitly visible:

- `harden-api-credentials` task 3.4: the owner deferred the real Last.fm account
  test on 2026-10-25. Automated credential tests and the web build pass; linking
  stays **partial** until the real flow succeeds.
- `deploy-on-stache-rack`: first rack rollout and its infrastructure records are
  still pending. Preparation tasks being complete does not mean deployment works.

These checks remain open while Phase 1 code work proceeds, as authorized by the
owner on 2026-10-25. Neither change should be archived as fully verified yet.

## Phase 1: module boundaries

Implement ADR 0001: a canonical `sidetrack` Python package with `identity`,
`catalog`, `listening`, `club`, and `analysis` modules. Modules own their tables;
cross-module writes go through public functions. Enforce boundaries with
import-linter in CI and preserve existing API and database contracts.

Do not implement the later phases while moving code. Postgres-backed background
jobs are Phase 2 (ADR 0002); per-user API authorization is Phase 3. Audio analysis
starts with the separate benchmark described by ADR 0004.
