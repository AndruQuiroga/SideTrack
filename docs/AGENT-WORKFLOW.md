# Agent workflow

Planning takes judgement, and a good plan makes implementation mechanical. So the capable model
plans and reviews, and a faster one implements. OpenSpec is the hand-off between them: a change's
tasks are the instructions, and each task's named test is how both sides know it's done.

| Role        | In Claude Code                       | Does                                                                                 |
| ----------- | ------------------------------------ | ------------------------------------------------------------------------------------ |
| Planner     | Opus, the main session               | Proposes and revises changes, picks what's ready, reviews, merges, deploys, archives |
| Implementer | Sonnet, the `opsx-implementer` agent | Implements one ready change in its own worktree                                      |
| Owner       | The person                           | Decides, listens, approves production work, and runs root steps                      |

## When a change is ready

The planner hands a change over only when all of these hold:

- Every change it depends on is merged.
- Every task names the test or check that proves it.
- Nothing in it depends on a decision that hasn't been made.
- Each task that needs the rack, production or the owner is marked `(owner)`.
- Its statements about current state still hold. Drafts go stale as other changes land.

## Implementer rules

- Work on one change, in one worktree, on a branch named `impl/<change>`.
- Commit after each task. Don't push, open or merge a PR, or archive.
- Change only what the tasks describe. A bug found on the way goes in the report.
- Leave `proposal.md`, `design.md` and `specs/` alone. Only tick boxes in `tasks.md`.
- Never reach the rack, production, Portainer or real listening data. Fixtures are synthetic.

Stop and report when:

- The next task is marked `(owner)`.
- A task is unclear, or the design doesn't fit the code.
- Finishing would mean narrowing, skipping or weakening specified behaviour.
- A new dependency, service or ADR-level decision seems necessary.
- A test keeps failing after two honest attempts.

## Planner review

Before merging, the planner reads the diff against the spec, checks that each ticked task's proof
exists and passes, and reviews any choice the implementer reported. The planner resolves stale
generated files by regenerating them, opens the PR, and merges it once CI passes. `(owner)` tasks,
production work and archiving stay with the planner and the owner.

## Running changes side by side

Two changes can run at once only if they don't compete:

- Only one running change may add a migration, because each takes the next number.
- They shouldn't edit the same domain module.
- Both may edit `docs/status.yaml`; the planner regenerates `docs/STATUS.md` when merging.
