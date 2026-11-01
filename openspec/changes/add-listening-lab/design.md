# Design

## Context

See proposal.md. This is a workbench, so speed matters, but the data is real and personal. Two
project rules shape it: no audio over HTTP, and no fake data under `services/`.

## Goals / Non-Goals

**Goals:**

- Make a new demo cheap: one data builder and one page.
- Let the owner see, hear and judge an idea on their own music.

**Non-Goals:**

- A durable product, accounts, or polish beyond what makes a demo readable.
- Proving any claim. Passing the lab doesn't pass an evaluation gate.

## Decisions

### Decision 1: Static pages, no server

`audio-lab lab build --out DIR` writes an `index.html` and one page per demo, with data embedded.
The owner opens it from disk. Audio plays through `file://`, as the review pages do. Alternative: a
loopback server, rejected because a page served over `http://` can't play `file://` audio, so it
would have to serve audio, which the project forbids.

### Decision 2: A demo is a builder and a template

Each demo lives in `lab/demos/<name>.py` with `build(context) -> dict` and a `<name>.html` beside
it. The shell finds the registered demos, and a demo missing an input is listed as `unavailable`
with the reason, so one gap doesn't stop the site. Output is refused inside the repo.

### Decision 3: The snapshot is SQL, run by the operator

`scripts/lab_snapshot.sql` writes one CSV row per play: time, artist, title, session start, session
end, effective kind and the preferred asset's SHA-256 from `track_audio_links` (full before preview).
It only reads, so it needs no release, and audio-lab keeps never touching the database. Doubtful
sessions, those over 30 listens an hour with at least 20 listens, carry a `doubtful_timing` flag.

### Decision 4: Tangents are measured in the named axes

The space is the owner's kept axes, from `dimensions` and its decision file. Six interpretable
numbers let a tangent read "into Chaos", where 512 dimensions can't say anything. A session's
position is the play-weighted mean of its tracks. Sessions with under 3 plays with audio, autoplay
sessions and doubtful sessions are skipped, and the skip counts are reported.

### Decision 5: Baseline, tangent and drift

- **Baseline:** the mean position of the previous 90 days of included sessions, needing 10 or more.
- **Deviation:** distance from the baseline, in units of the baseline's own spread. Axes are first
  scaled by their spread across the library, so no axis dominates. Sessions in an open run or a
  returned tangent stay out of the baseline.
- **Tangent:** a run of at least 2 sessions and 8 plays above the threshold, ending when 3 sessions in
  a row come back below it.
- **Drift:** a run still away after 45 days. It's marked as not having returned, and the baseline
  catches up. A drift is a candidate era for `add-listening-journey`.
- **Gaps:** 30 days with no usable sessions ends any open run, marked `gap`. A gap is never a return.
- **Open branches:** a run ended by a gap, or still going when the data ends, is kind `open`. It's
  drawn with a dashed end, and it isn't counted as a tangent.
- **Presets:** strict, normal and loose thresholds of 2.5, 2.0 and 1.5. All are working values,
  chosen to look at, and the demo says so.

### Decision 6: What the timeline draws

Time runs along the trunk. A tangent leaves at its start and rejoins at its end, and a drift leaves
and doesn't rejoin. Height is peak deviation, and the side and colour come from the axis that moved
most. Dashes mark gaps. Hovering shows dates, the named axes and top tracks. Clicking opens the tracks
to play. Branches inside branches are left for a later version, once single-level branches look right.

### Decision 7: Verdicts are a file

Each demo has keep, rework and drop with a note, exported as `lab-verdicts.json`. `localStorage` holds
drafts, and the page works without it.

## Risks / Trade-offs

- [Coverage is uneven over time] → Skipped counts and gaps stay visible, and older years may be sparse.
- [Doubtful timestamps create false sessions] → They're flagged and skipped by default.
- [Axes come from 233 tracks] → `dimensions` is rerun on the larger library, and the owner names the
  axes again if they change.
- [Tangents are mostly artist binges] → Hover shows the tracks, so it's visible. A later version can
  compare against artist shares, as `add-listening-journey` plans.
- [Personal data on disk] → Everything stays outside the repo, and the site has no network calls.

## Open Questions

None that change what gets built. The presets and the look are what the demo exists to test.
