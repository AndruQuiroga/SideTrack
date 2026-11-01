# Proposal

## Why

The vision's "themes" are recurring sound-worlds in a listener's library. MuQ-MuLan groups genres at 5? chance and has a text tower, so clusters can be found and named from audio alone, which matters because crowd tags don't cover this music.

## What Changes

- Clustering a user's embedded library into themes, versioned and reproducible.
- Text embeddings of a controlled vocabulary (MTG-Jamendo tags plus a curated electronic-subgenre list) computed by the GPU worker's text tower and stored.
- Naming each theme by its library-calibrated nearest terms, with representative tracks; users can rename.
- Zero-shot tags per asset from the same vocabulary.

Out of scope:
- Weekly theme shares (weekly profile change).
- Free-text search (a later `add-text-audio-search` change reuses the text table).
- LLM captioning (doesn't fit the GTX 1070; docs/research/MUSIC-ANALYSIS.md ?3).

## Capabilities

### New Capabilities
- `analysis/sound-themes`: clustering a library into named themes and zero-shot tags.
- `analysis/text-embeddings`: storing text-tower vectors for vocabulary terms in the joint space.

### Modified Capabilities
None.

## Impact

- **Observed:** text tower unused; GPU worker loads MuQ-MuLan (`services/gpu-worker`). Affected: `sidetrack/analysis/`, GPU job runner, migrations, docs/AUDIO.md.
