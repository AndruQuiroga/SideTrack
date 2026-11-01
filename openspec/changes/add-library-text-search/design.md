# Design

## Context

See proposal.md (Why, Impact) for motivation and the observed state. Constraints that shape
the approach:

- MuQ-MuLan, `torch` and `muq` live only in the GPU worker image; the API and CPU worker
  images do not have them (`sidetrack/analysis/embeddings/muq_mulan.py`).
- The GTX 1070 is shared, 8 GB, Pascal (fp32 in practice). MuQ-MuLan peaked at 2.8 GB in
  the benchmark; that is not a guarantee of end-to-end throughput or of co-residence with
  other models. Swarm does not reserve the GPU between services
  (docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md section 1).
- Audio vectors are one mean-pooled vector per asset over at most the first 180 s; no
  window vectors are stored, so a query can only match a track summary, not a section
  (notes section 1, "Text-to-audio labels and search" in section 2).
- The library is small (862 assets), so exact pgvector cosine over the eligible set is
  cheap; no approximate index is needed.
- Postgres is the only stateful service; background work uses the existing Postgres-backed
  queue with `default`, `musicbrainz` and `gpu` queues (`openspec/specs/platform/background-jobs`).

Research cautions carried into this design (notes section 2, "Text-to-audio labels and
search", and section 3, "A practical validation protocol"): cosine is not a probability;
two-tower models are prompt-sensitive and use musical context weakly; a per-term library
z-score is a candidate ranking heuristic, not calibration or a modality-gap correction;
evaluation must vary prompt wording, include close confusions and hard negatives, allow
abstention and show representative tracks.

## Goals / Non-Goals

**Goals:**
- A query is encoded at most once per user and model revision, on the GPU worker, without
  making the API depend on the GPU.
- Ranking method and abstention threshold are data from an accepted evaluation, not
  constants chosen in code.
- Every response is self-describing: status, coverage, model, revision, method.

**Non-Goals:**
- Sub-second first-query latency. A queued first encoding is acceptable for one owner and
  a few members; repeat queries are immediate.
- A shared, cross-user query cache.
- Ranking audio the user has not listened to (discovery from previews is a separate idea).

## Decisions

### 1. Query encoding: queued GPU job with a per-user stored encoding

The API stores the query, enqueues `analysis.encode_text_query` on the `gpu` queue and
returns `pending` with the job ID; the web page polls the existing job-status route
(owner-only by `identity/personal-data-visibility`) and then fetches results. Results are
ranked on read in the API with pgvector from the stored query vector, so changing the
ranking configuration never needs the GPU.

Alternatives considered:
- **Synchronous on-demand GPU call from the API.** Rejected: the API would need the model
  and CUDA, or a blocking RPC to the worker; the GPU is not reserved and may be busy with
  an embedding backfill, so requests would hang or fail unpredictably.
- **Load the text tower on CPU in the API process.** Rejected for now: adds `torch`, `muq`
  and the checkpoint (gigabytes) to the API image and memory on a VM shared with other
  services (notes section 1); CPU latency is unmeasured. Revisit only with a measurement
  and an ADR, because it changes the API image's dependencies.
- **A dedicated always-on text-encoding service.** Rejected: a new service is new
  infrastructure needing an ADR (AGENTS.md), and holding the model resident competes for
  VRAM with embedding jobs.
- **Vocabulary-only search** (match the query to precomputed vocabulary terms from
  `add-sound-themes`). Rejected as a substitute: it silently changes what the user asked.
  It may become a separate, explicitly labelled "browse suggested terms" feature.
- **Precompute encodings for likely queries.** Rejected: free text has no useful finite
  set; the per-user stored encoding gives the same benefit for repeats.

### 2. The worker loads the text tower per job, as embedding does today

`MuQMuLan` loads once per job (`muq_mulan.py`). The text job does the same, so a single
query pays model load time. Task 2.4 measures cold-start and end-to-end latency on the
1070. Keeping the model warm between jobs is deferred: it holds VRAM while other GPU jobs
may need it, and it would change the GPU worker's lifecycle for every job type.

Alternative considered: keep the text tower resident with an idle timeout. Deferred until
the measurement shows per-job load is unacceptable and VRAM coexistence is measured.

### 3. Queue priority

The Postgres queue is FIFO within a queue; a query submitted during an 862-asset backfill
waits behind it. Accepted for this change because backfills are operator-started and rare
(`analysis/audio-embeddings`: backfill is explicit). The pending message says the query
is waiting for the analysis worker. A priority lane is a follow-up if measurement shows it
matters.

### 4. Ranking configuration is recorded evaluation output

A versioned configuration file in the repository (for example
`sidetrack/analysis/search/ranking.toml`) names the method (`raw_cosine` or
`library_z`), version, abstention threshold and the evaluation run ID, plus the owner's
acceptance date. No file, or one not marked accepted, means `not_evaluated`. Keeping it in
the repo makes the gate reviewable in a PR and needs no new table.

Alternatives considered: an environment flag (rejected: it can enable search without
recording which evaluation justified it); a database row (rejected: harder to review than
a committed file, and only the operator changes it).

### 5. Ranking candidates and abstention

Candidates evaluated in task 1.x: raw cosine; a library-relative score (the query's cosine
z-scored against its distribution over the user's eligible library); a metadata baseline
(query words in artist/title); and a random control. The z-score is treated as a ranking
heuristic only; with very low variance it becomes unstable, so it is guarded by a minimum
standard deviation and falls back to `no_confident_match` rather than amplifying noise.

The abstention threshold is chosen from evaluation: hard-negative prompts (sounds the
owner confirms are absent from the library) should mostly produce `no_confident_match`,
while prompts with confirmed matches still return them. The chosen operating point and its
measured false-match rate are recorded with the configuration. Neither the score nor the
threshold is shown as a probability.

### 6. Eligible library and one row per track

A user's library is the distinct catalog tracks in their listens (from
`import-listenbrainz-history`). Each track is represented by its preferred asset from
`resolve-listens-to-audio` (full over preview, confirmed over unverified, embedded over
not), filtered by the full/preview choice. Only `audio_for_track` status `ok` is
eligible; `no_audio`, `ambiguous` and `no_embedding` tracks are counted in coverage
(`no_link`, `ambiguous`, `no_embedding`) and never ranked, so an uncertain identity link
cannot surface as a confident result. Search never creates or confirms a link: sonic
similarity is not recording identity. This avoids listing a full track and its own
preview as two results, which `similar_assets` already guards against for neighbours.
Versions and edits of a recording are not merged (recognition is a separate change).

### 7. Personal data

New analysis-owned tables: `text_queries` (user, normalised text, original text, model,
revision, dimension, vector, created/last-used timestamps) and `text_query_feedback`
(user, query, track, mark, timestamps), both cascading from `users`. The JSON export is
served by an owner-only route. Query text can be sensitive; it is never logged in job
results, and job payloads carry only the query row ID.

## Risks / Trade-offs

- [Prompt sensitivity: paraphrases reorder results] -> evaluation measures overlap of
  top-10 lists across paraphrases; the page says rewording can reorder results.
- [Cosine scores drift with library composition] -> threshold is tied to an evaluation
  run and revision; a new model revision or a large library change requires re-evaluation
  before the configuration is re-accepted.
- [Modality gap: text and audio vectors occupy different regions] -> do not compare raw
  scores across queries; rank within a query only; z-score is not claimed to fix it.
- [First-query latency from model load and FIFO queue] -> measured in task 2.4; pending
  state is explicit; deferred warm-model and priority options.
- [GPU contention with embedding or other services] -> one GPU job at a time on the
  existing worker; MuQ is not enabled so no co-residence is assumed.
- [The first 180 s only] -> analysed duration shown per result and in the explanation.
- [Low coverage makes results misleading] -> coverage shown on every response and page.
- [CC BY-NC weights] -> personal, non-commercial use only; re-check the pinned card.
- [Search history is personal data] -> owner-only, exportable, deletable, cascaded.

## Migration Plan

1. Migration adds the two tables; no backfill.
2. Deploy GPU worker with the text-encoding task, then API and web. Search reports
   `not_evaluated` until the accepted configuration is committed.
3. Run the evaluation, record the owner decision, commit the configuration, redeploy.
4. Rollback: remove the configuration file (search returns `not_evaluated`); the tables
   can stay or be dropped by a down-migration.

## Open Questions

- Retention for stored queries beyond "until the user deletes them": a default expiry may
  be added later without changing the specs' delete and export behaviour.
- Whether CPU text encoding is fast enough to revisit Decision 1 (needs a measurement in
  the audio-lab environment, and an ADR if adopted).
