# Design

## Context

See `proposal.md`. The ambiguity between empty and missing distributions warrants a short design even though this correction has no schema or service changes. Current shared data-honesty tests mostly inspect forbidden strings and do not detect arithmetic-derived presence.

## Goals / Non-Goals

**Goals:** Preserve supplied aggregates exactly and render missing evidence as missing.

**Non-Goals:** Build presence tracking, polling, or the UX redesign.

## Decisions

- Remove `livePresenceCopy` and unconditional live-listener/update claims. The current API has no evidence to display them; replacing them with different invented counts would retain the defect.
- Use returned histogram bins only. With zero supplied ratings, show No ratings yet. With positive or unknown count and missing bins, show Distribution unavailable. A zero-count bin has zero width; remove artificial minimum widths that imply positive values.
- Add rendered-output tests in `apps/web/tests/club-data-honesty.test.cjs` covering varying week counts, missing histograms, supplied bins, zero bins, and omitted live claims. Keep fixtures within tests.
- Update `docs/status.yaml` to cite this test only after it passes and regenerate the status document. Do not weaken existing main-spec scenarios.

## Risks / Trade-offs

- [UI loses decorative activity copy] -> Real counts and schedules still provide useful context.
- [Shared components are later replaced] -> Preserve behavior tests as a prerequisite for the redesign.
