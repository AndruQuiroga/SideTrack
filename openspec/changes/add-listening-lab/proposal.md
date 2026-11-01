# Proposal

## Why

Sidetrack has more analysis ideas than it can responsibly build: six named sound dimensions, a
listening journey, sound worlds, a sound bridge and more. A production feature costs a migration,
routes, a page and a gate, and the owner can't tell whether an idea is any good until they can see
it on their own music and hear the tracks behind it. The owner wants quick tests and demos first,
and production later for what survives.

The owner also proposed a new view: a timeline where listening leaves its usual sound on a tangent
and comes back, drawn like branches leaving and rejoining a trunk. It's the first demo here, and it
sharpens `add-listening-journey`: a tangent is a shift that came back, and an era is one that stayed.

## What Changes

- **The Listening Lab:** a local site, built into a folder outside the repo and opened from disk.
  Its home page lists the demos, each with a keep, rework or drop verdict that exports to a file.
- **A listening snapshot:** a read-only SQL export of one user's plays, with session kinds and the
  linked asset for each play, kept outside the repo.
- **Tangent detection:** finds runs of sessions that leave a trailing baseline, says whether they
  returned, and describes each by the owner's named axes and its tracks.
- **Demo 1, Tangent timeline:** the trunk and branches, with zoom, hover details, playable tracks,
  gaps shown as gaps, and strict, normal and loose presets.
- **Demo 2, Sound signature:** the owner's named axes for each year, and how they drifted.
- **Demo 3, Track explorer:** pick a track, hear it, and see its nearest tracks and axis positions.

Out of scope:

- Production code, tables, routes or pages. The snapshot SQL only reads.
- A server of any kind. Audio is never served over HTTP (ADR 0007).
- Mock or invented data in the repo. Demos use real data and report what's missing. Mock-ups of
  unbuilt ideas are private artifacts.
- Search by description, which needs the text tower live. It's a later demo.
- Other listeners. The lab is for the owner.
- Saying what a tangent meant. It's an estimated change in sound, never a mood or a life event.

## Capabilities

### New Capabilities

- `analysis/listening-lab`: the local demo site, listening snapshot, tangent detection and first
  three demos.

### Modified Capabilities

None.

## Impact

Current state:

- **Observed:** `services/audio-lab` writes self-contained pages (`report/template.html`,
  `dimensions_review.html`) that play local files through `file://`, and it never reads the database
  (docs/MODULES.md). `AGENTS.md` forbids serving audio over HTTP and fake data under `services/`.
- **Observed:** `dimensions` writes `scores.csv` with per-track axis scores, and the owner named six
  axes on 233 tracks (docs/AUDIO-BENCHMARK.md).
- **Observed:** production holds 74,907 listens in 5,420 sessions. `track_audio_links` links 392
  tracks, 9.3% of plays. An overnight fetch of 2,000 more tracks is running.
- **Observed:** 105 sessions, about 5,900 listens, claim impossible speeds, so their timing is
  doubtful. They're likely batches of offline scrobbles or imports.
- **Assumed:** after the fetch, enough sessions have audio to draw a useful timeline. Task 5.2 measures
  that, and gaps stay visible either way.
- **Assumed:** new tracks can be embedded on the RTX 5070 with the existing `embed` command.

Affected:

- `services/audio-lab/src/audio_lab/lab/` (new), its CLI and tests.
- `scripts/lab_snapshot.sql` (new), `docs/AUDIO.md`, `services/audio-lab/README.md`, `docs/status.yaml`.
- `add-listening-journey`: reviewed against what this finds before it's built.

Dependencies: none for the code. The real run needs the overnight fetch imported and linked.
