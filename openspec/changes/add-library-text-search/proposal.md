# Proposal

## Why

About half the owner's tracks are unknown to AcoustID/MusicBrainz, so crowd tags can't
describe them, but MuQ-MuLan is a joint audio/text model: its text tower can turn a phrase
such as "melodic bass with airy vocals" into a vector in the same space as the 862 stored
audio vectors. Searching one's own library by describing a sound is the highest
value-for-cost idea in docs/research/MUSIC-ANALYSIS.md section 7 and mockup 9 of
docs/research/MOCKUPS.md. It is also easy to present dishonestly: a cosine similarity is not
a probability, results move when a prompt is reworded, and most of the library may have no
eligible audio. This change defines the search so those limits are visible and so it ships
only after a task-specific evaluation.

## What Changes

- **Query encoding.** A user's search text is encoded by the MuQ-MuLan text tower of the
  same checkpoint revision as the stored audio vectors, as a job on the existing `gpu`
  queue. The API never loads the model. Encoded queries are kept per user, so repeating a
  query does not need the GPU again.
- **Ranking over the user's own eligible library.** Results are tracks the requesting user
  has listened to that resolve to audio with a current embedding of the same model,
  revision and pipeline. The ranking method (raw cosine or a library-relative variant) and
  an abstention threshold come from a recorded, owner-accepted evaluation; until one
  exists the search reports `not_evaluated` instead of results.
- **Honest result states.** `pending`, `ok`, `no_confident_match`, `no_eligible_audio`,
  `unavailable`, `failed` and `not_evaluated` are distinct. Every result list carries
  coverage (eligible tracks out of the user's listened tracks), the model and revision,
  the ranking method version, and per result whether it is a full track or a preview and
  how much audio was analysed. No similarity is shown as a percentage, probability or
  confidence.
- **Private history and feedback.** Search history and optional "useful" / "not relevant"
  marks are owner-only personal data: listable, exportable as JSON, deletable by the user,
  and removed with the account. Feedback never retrains anything.
- **Web page** at `/listening/search` (mockup 9) with the coverage line, filters for full
  tracks and previews, a "how this list was ranked" panel that states prompt sensitivity,
  and accessible, metadata-only results.
- **Evaluation and owner gate.** A text-search evaluation in `services/audio-lab` with
  prompt variants, close confusions and hard negatives, comparing raw cosine, a
  library-relative score, and random and metadata baselines; the owner records a decision
  before the feature is enabled.

Out of scope:
- Vocabulary embedding and zero-shot tags (`add-sound-themes`, capability
  `analysis/text-embeddings`); this change reuses its text-tower loading and provenance.
- Searching other members' libraries, the club, or audio that the user has not listened to.
- Audio playback, audio URLs or file paths in any response (ADR 0007). Acquiring audio for
  unmatched tracks.
- Timestamped or section-level explanations ("this part matched"): the pooled vectors cannot
  support them (`add-timestamped-audio-windows` is a separate proposal).
- Other text/audio models (CLAP, MERT) and fine-tuning on feedback.
- An always-on text-encoding service or loading PyTorch into the API image (rejected in
  design.md; each would need an ADR).
- Any claim that a phrase correctly describes a track, or any calibrated confidence.

## Capabilities

### New Capabilities
- `analysis/text-audio-search`: encoding a user's free-text query in the joint space,
  ranking that user's eligible library against it with an evaluated method and abstention,
  reporting coverage and provenance, and keeping query history and feedback as private,
  exportable, deletable data.
- `web/library-search`: the `/listening/search` page that shows those results, their
  coverage, distinct empty and failure states, and the ranking explanation, without audio.

### Modified Capabilities
None. `analysis/audio-embeddings`, `web/data-honesty` and
`identity/personal-data-visibility` are unchanged; this change follows them.

## Impact

Current state:
- **Observed:** production holds MuQ-MuLan vectors for 862 assets, one pooled 512-d vector
  per asset: mono decode, non-overlapping 10 s windows, a final partial window kept if at
  least 3 s, the first 180 s only, mean-pooled and L2-normalised; window vectors are not
  stored (`sidetrack/analysis/embeddings/registry.py`, `sidetrack/analysis/embeddings/audio.py`,
  docs/STATUS.md "Audio embeddings").
- **Observed:** "No HTTP route or page uses embeddings yet" (docs/STATUS.md). The only
  consumer is `similar_assets`, an exact pgvector cosine ranking within one model, revision
  and pipeline (`sidetrack/analysis/embeddings/neighbours.py`).
- **Observed:** `MuQMuLan` loads the model once per job and only embeds audio windows; the
  text tower is unused. `torch` and `muq` exist only in the GPU worker image and a missing
  library or CUDA is reported as unavailable (`sidetrack/analysis/embeddings/muq_mulan.py`).
- **Observed:** the existing `GET /search` route is a metadata `ILIKE` search over users,
  albums and tracks (`sidetrack/api/routes/search.py`); it is unchanged. `/discover` renders
  a feature-unavailable notice (`apps/web/app/discover/page.tsx`).
- **Observed:** audio assets carry `kind` (full or preview) and an optional `duration_s`;
  `track_id` is null for all production assets until links exist
  (`sidetrack/analysis/models.py`, `openspec/changes/resolve-listens-to-audio/proposal.md`).
- **Observed (dated):** the GTX 1070 has 8 GB shared VRAM; MuQ-MuLan peaked at 2.8 GB and
  MuQ at 5.3 GB in run `20261027-172855`, so the two are not assumed co-resident; Swarm does
  not reserve the GPU between services (docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md
  section 1).
- **Assumed:** encoding one short query with the text tower is small next to model load
  time on the 1070; cold start and end-to-end latency are unmeasured (task 2.4 measures).
- **Assumed:** MuQ-MuLan weights are CC BY-NC 4.0 (model card), compatible with this
  personal, non-commercial deployment; re-check the pinned revision's card.

Dependencies:
- `add-sound-themes` (capability `analysis/text-embeddings`) for the text-tower loader and
  text-vector provenance.
- `resolve-listens-to-audio` (capability `analysis/listen-audio-resolution`) for which audio
  represents a user's listened track and for coverage.
- `import-listenbrainz-history` for the listened tracks that define a user's library.

Affected:
- `sidetrack/analysis/` (query encoding job, query and feedback tables, search read model),
  `sidetrack/analysis/routes/`, `sidetrack/job_runner.py`, `services/gpu-worker`,
  `migrations/`, `services/audio-lab` (evaluation), `apps/web` (`/listening/search`),
  `packages/api-client`.
- Docs: `docs/AUDIO.md`, `docs/AUDIO-BENCHMARK.md`, `docs/MODULES.md`, `docs/status.yaml`.
