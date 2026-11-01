# Proposal

## Why

The owner accepted DEAM for personal, non-commercial use on 2026-10-31. The rights register can't
say that. Its only status that lets a claim be approved is `recorded`, which means the source
states its terms, and DEAM's terms for the files used are still unknown. Recording DEAM as
`recorded` would be false.

## What Changes

- A new rights status, `owner_accepted`: the terms remain unconfirmed, and the owner accepts that
  for a stated scope. It doesn't mean rights are cleared.
- It needs an `acceptance` block with the date, who accepted and the scope, or the check fails.
- A claim citing an `owner_accepted` dataset can be approved. `rights_unconfirmed` still blocks.
- DEAM's audio and annotations are recorded as accepted for personal, non-commercial use.

Out of scope:
- Approving `mood-estimate`. It still needs an artist-grouped run and a complete gate record.
- Any other dataset, and any statement that a dataset's rights are cleared.
- Commercial use. Sidetrack is a personal project, and any change to that voids this acceptance.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `analysis/evaluation-gates`: the rights register can record an owner's scoped acceptance.

## Impact

- **Observed:** `scripts/check_evaluations.py` allows approval only for `recorded`.
- **Observed:** `docs/evaluations/datasets.yaml` marks DEAM audio and annotations
  `rights_unconfirmed`, and `register.yaml` lists that as missing evidence for `mood-estimate`.
- Affected: `scripts/check_evaluations.py`, `tests/test_check_evaluations.py`, `docs/evaluations/`.
