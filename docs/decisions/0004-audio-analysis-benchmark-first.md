# 0004: Audio analysis starts as a benchmark

- Status: accepted
- Date: 2026-10-25

## Context

No real audio model has ever run in this project; the pre-reboot adapters returned fake numbers. The project packet recommends proving models on ~100 tracks before building product around them.

## Decision

Build a standalone benchmark CLI first (MuQ, MuQ-MuLan, MERT-v1-95M, CLAP) that writes versioned results to Parquet and measures the GTX 1070 Ti. Integrate into the `analysis` module (pgvector, `gpu` queue) only after one model produces neighbours the owner agrees with on obscure tracks.

## Consequences

- Each model adapter declares its checkpoint, license, sample rate and status.
- Embeddings from different models are never compared to each other.
- **2026-10-27:** MuQ-MuLan passed the gate (run `20261027-031711-c7c3698`); [ADR 0010](0010-muq-mulan-audio-embeddings.md) records how it is integrated.
