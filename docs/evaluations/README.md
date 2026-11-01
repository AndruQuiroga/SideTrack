# Analysis evaluation gates

An audio-analysis claim (a mood estimate, a suggested theme, "nearest in your library", a
tempo) may reach a user only after a recorded evaluation passes **and the owner approves it**.
Dataset scores never replace the owner's listening. The protocol is section 3 of the
[research notes](../research/MUSIC-ANALYSIS-RESEARCH-NOTES.md#3-evaluation-data-and-rights);
the tooling extends the benchmark of [ADR 0004](../decisions/0004-audio-analysis-benchmark-first.md)
without changing it, and the benchmark itself is described in
[AUDIO-BENCHMARK](../AUDIO-BENCHMARK.md).

| File                          | What it holds                                               |
| ----------------------------- | ----------------------------------------------------------- |
| `register.yaml`               | One entry per claim: its gate status and the revisions used |
| `datasets.yaml`               | One entry per evaluation dataset: terms, gaps, acquisition  |
| `summaries/<claim>/<id>.json` | Aggregate summary of one evaluation record (committed)      |

## Statuses

| Status         | Meaning                                                                          |
| -------------- | -------------------------------------------------------------------------------- |
| `approved`     | Complete evidence, an owner `approve`, every cited dataset usable. May be shown. |
| `gate_pending` | The record is complete but the owner has not decided, or asked for corrections.  |
| `incomplete`   | Evidence is missing, or a cited dataset is unregistered. Names what is missing.  |
| `rejected`     | The owner rejected it. The note is kept in the record.                           |
| `stale`        | It was approved for revisions the feature no longer uses.                        |

Only `approved` permits a claim to be user-facing. Each feature's own change decides how its
product renders the other states; this directory does not gate any route.

## Where things live

- **Evaluation record** (`record.json`): outside the repo, next to the audio-lab run on the HDD.
  It holds per-item results and example titles. Never commit it.
- **Summary**: `audio-lab gate summarize` writes aggregate figures and counts only (no artist,
  title, path or per-track value), to `summaries/<claim>/<record-id>.json`.
- **Dataset audio and annotation files**: outside the repo. Only aggregate figures enter it.
- **Dataset rights**: `datasets.yaml` records what each source says and what is unknown. It
  is not legal advice and never says that rights are cleared. Every entry keeps `recheck: true`
  until the terms are verified at the exact revision used. Audio is obtained by the owner by
  hand; evaluation tooling never runs yt-dlp or fetches audio.

## The owner gate

1. Run `audio-lab gate check` on the record; fix what it names.
2. `audio-lab gate review` writes an offline page of examples (including held-out obscure,
   electronic and altered tracks). Listen, then export `decision.json`: `approve`, `reject` or
   `correct`, with notes and corrections.
3. `audio-lab gate decide` adds the decision to the record; `gate summarize` writes the summary.
4. Set the claim's `status` and `summary` in `register.yaml`.

A single rater approves the claim for the owner's library only, and the summary says so. A
claim for the whole club needs its own entry. The commands are in
[services/audio-lab/README.md](../../services/audio-lab/README.md#evaluation-gates).

## What CI checks

`python scripts/check_evaluations.py` fails when:

- an entry is `approved` without a summary that records an owner `approve`;
- the summary's model, checkpoint, probe, pipeline or vocabulary revision differs from the entry's
  `feature_revisions` (the entry should be `stale`);
- an entry cites a dataset missing from `datasets.yaml`, or one whose rights for that use are
  not `recorded`, and is marked anything but `incomplete`;
- a capability listed under an entry's `capabilities` is `works` in `docs/status.yaml` while the
  entry is not `approved`.

It warns when a dataset was last reviewed more than 365 days ago.
`python scripts/check_evaluations.py --links` also checks the relative links in these docs.

## Adding a claim

Add an entry to `register.yaml` with `status: incomplete`, the `feature_revisions` the feature
declares, the `datasets` it cites (each with a `use` of `audio` or `annotations`) and the
`capabilities` in `docs/status.yaml` that depend on it. A feature change copies its live revisions
into the entry when it ships.
