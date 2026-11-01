# Proposal

## Why

The product vision's "themes" are recurring sound-worlds in a listener's library. MuQ-MuLan groups genres well above chance and has a text tower. Clusters can therefore be proposed and described from audio alone, which matters because crowd tags do not cover this music. Clusters and text labels are model-relative suggestions, though, not a cultural taxonomy. The research found substantial prompt sensitivity in two-tower models (notes §2, "Text-to-audio labels and search"). The design must evaluate stability and allow abstention instead of assuming any algorithm or calibration works.

## What Changes

- Clustering a user's linked, embedded tracks into candidate themes, versioned and reproducible. The algorithm, thresholds and fallback are treated as hypotheses chosen by an evaluation task.
- Text embeddings of a versioned, curated vocabulary, computed by the GPU worker's text tower and stored. The vocabulary is built from MTG-Jamendo tags plus terms curated for the owner's actual library. It is not assumed to be complete.
- Describing each theme by ranked vocabulary terms plus representative tracks. The ranking method (raw cosine, library-relative rank or per-term z-score) is a candidate heuristic, selected by evaluation. A theme with no term passing the threshold shows `no_confident_label`.
- Per-asset suggested terms from the same vocabulary, with the same abstention rule.
- User renames that survive rebuilds when a theme can be matched, and are reported when it cannot.

Out of scope:
- Weekly theme shares (`add-weekly-listening-profile`).
- Free-text search (`add-library-text-search` reuses the text table).
- The explorer UI and label feedback (`add-sound-world-explorer`).
- LLM captioning (`explore-lyrics-and-captioning`).
- Any claim that a term is a probability or that a cluster is a real genre.

## Capabilities

### New Capabilities
- `analysis/sound-themes`: candidate themes clustered from a library, with suggested terms, abstention and renames.
- `analysis/text-embeddings`: text-tower vectors for vocabulary terms, stored in the joint space.

### Modified Capabilities
None.

## Impact

- **Observed:**
  - The text tower is unused in production.
  - The GPU worker loads MuQ-MuLan for audio only (`services/gpu-worker`, `sidetrack/analysis/embeddings/registry.py`).
  - There is one pooled vector per asset from the first 180 s.
- **Assumed:** text encoding of a few hundred terms fits alongside audio jobs on the GTX 1070. MuQ-MuLan's measured peak is 2.8 GB; this will be confirmed in task 1.
- Depends on `resolve-listens-to-audio` (linked tracks), and on `add-music-analysis-evaluation-protocol` for the evaluation record.
- Affected: `sidetrack/analysis/`, the GPU job runner, migrations, `docs/AUDIO.md`.
- Research: notes §2 (text labels), §3 (protocol), §6.4.
