# Design

## Context

See proposal.md. The page mixes judgement (is ratings "works"?) with facts (which routes exist). Only the facts can be derived; the judgement needs a human, but it can be held to evidence.

## Goals / Non-Goals

**Goals:** a page that can't silently go stale; claims tied to files that prove them; output an agent can read in one pass.

**Non-Goals:** running tests from the generator; scoring coverage.

## Decisions

**YAML source plus generated Markdown.** Agents and humans read Markdown; the YAML is small and reviewable in diffs. Alternative considered: front matter inside STATUS.md. Rejected because mixing input and output makes `--check` circular.

**Facts collected:**
- Routes: from `create_app()` with `SIDETRACK_ENV=development`. No database connection is made.
- Migration head: the revision no other migration names as `down_revision`.
- Specs: `openspec/specs/**/spec.md`.
- Changes: every `openspec/changes/*` except `archive`, with `- [x]` / `- [ ]` counts from `tasks.md`.

All sorted, and no timestamps except the YAML's `reviewed` date, so output is deterministic.

**Evidence is file paths, globs allowed.** Tests are the preferred evidence; config files are allowed for capabilities that are configuration (CI, image visibility). Existence is checked, but not that the file proves the claim; review covers that.

**Tested in-process.** A pytest module checks validation errors and that the committed page is current. CI also runs `--check` as a separate step, so the failure message is obvious.

## Risks / Trade-offs

- [Every route change now requires regenerating the page] → That's intended; the failure message names the command.
- [Evidence can be a file that doesn't really prove the claim] → Code review; the rule still stops claims backed by nothing.
