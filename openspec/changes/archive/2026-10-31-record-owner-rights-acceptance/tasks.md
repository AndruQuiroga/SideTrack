# Tasks

## 1. Owner acceptance

- [x] 1.1 Add the `owner_accepted` status and the required `acceptance` block to `scripts/check_evaluations.py`; verify `tests/test_check_evaluations.py::test_owner_acceptance_allows_approval`, `::test_owner_acceptance_needs_a_scope` and `::test_rights_unconfirmed_blocks_approval`
- [x] 1.2 Record the owner's DEAM acceptance in `docs/evaluations/datasets.yaml`, and update `register.yaml`, the evaluations README and `docs/AUDIO-BENCHMARK.md`; verify `::test_seed_datasets_registered` and `scripts/check_evaluations.py --links`. No ADR or status change is expected.
