# Design

## Context

See proposal.md and `docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md` §2 ("Text-to-audio labels and search"), §3 (protocol) and §6.4.

An earlier draft of this design claimed that a per-term z-score "counters the modality gap". The research does not support that claim, so it has been removed. A per-term z-score is one candidate ranking heuristic. It does not calibrate confidence or close the audio/text gap, and it is unstable when a term's variance is very low.

## Goals / Non-Goals

**Goals:**
- Reproducible candidate themes.
- Honest suggested terms with abstention.
- An evaluation that chooses the algorithm and ranking method.

**Non-Goals:**
- A definitive genre taxonomy.
- Probabilities.
- LLM captions.

## Decisions

1. **Clustering is a hypothesis.** Candidates are HDBSCAN (cosine, minimum cluster size around 8) and k-means with a silhouette-selected k as baseline/fallback. Task 2.1 compares them on stability across seeds and small corpus changes, on unassigned share, and on owner judgments of coherence. The previous fixed rule (fall back to k-means when more than 60% is noise) is kept only as a starting parameter for that comparison.
2. **Ranking method is a hypothesis.** Compare raw cosine, rank within the user's library, and per-term z-score. Use held-out labelled examples from the owner, plus prompt variants and hard negatives (close confusions such as dubstep versus riddim). The abstention threshold is chosen on the same data. The method version is stored with every label.
3. **Prompt templates.** Each term is embedded with several templates (for example "music with {term}" or "{term} track"). The evaluation records whether averaging templates helps.
4. **Vocabulary.** A versioned file in `sidetrack/analysis/vocabulary/`: MTG-Jamendo genre, instrument and mood/theme tags, plus terms curated for the owner's library. Terms are suggestions; genre also has cultural meaning audio cannot establish.
5. **Rename carry-over.** Use Jaccard overlap of membership between old and new themes, with a threshold of 0.5 as a starting value. Below that, report `rename_orphaned`.
6. **Tables.** `text_embeddings`, `sound_theme_builds`, `sound_themes`, `sound_theme_members`, `sound_theme_names`.

## Risks / Trade-offs

- **Prompt sensitivity and vocabulary bias.** Mitigated by multiple templates, abstention, representative tracks always shown, and feedback in `add-sound-world-explorer`.
- **Instability after library growth.** Builds are versioned, and renames carry over only with sufficient overlap.
- **First-180-s pooled vectors.** Themes reflect at most the first three minutes of each track.
- **GPU contention.** Text encoding is a small queued job on the shared card; it does not keep a model resident.

## Open Questions

- Should suggested per-asset tags be shown at all before label feedback exists? The default is to show them only in the explorer, marked as suggestions.
