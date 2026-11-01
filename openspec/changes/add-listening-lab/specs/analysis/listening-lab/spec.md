# Spec Delta

## Purpose

Defines the local Listening Lab: how it's built and opened, how it gets real listening data, how it
finds tangents, and what its first demos show.

## ADDED Requirements

### Requirement: The lab is a local site with no server

The lab SHALL build into a folder of pages opened from disk. It SHALL run no server, make no network request, and play audio only from local files. It SHALL refuse an output path inside the repository.

#### Scenario: Built site

- **WHEN** the lab is built
- **THEN** its pages load no network script, font or data, and audio sources use `file://`

#### Scenario: Output inside the repo

- **WHEN** the output path is inside the git working tree
- **THEN** the build fails and writes nothing

### Requirement: Demos use real data and report what's missing

Every value a demo shows SHALL come from the listener's snapshot, runs or decisions. A demo missing an input SHALL be listed as `unavailable` with the reason, and the other demos SHALL still build.

#### Scenario: Missing input

- **WHEN** the snapshot is absent
- **THEN** the demos that need it are listed as `unavailable` naming the snapshot, and the rest build

### Requirement: The listening snapshot only reads

The snapshot SHALL write one row per play with its time, artist, title, session boundaries, effective session kind, preferred asset and a doubtful-timing flag. It SHALL change no data.

#### Scenario: Reviewed session

- **WHEN** a night-flagged session has a `keep` override
- **THEN** its plays carry the effective kind `keep`

#### Scenario: Track with two assets

- **WHEN** a track links to a full asset and a preview
- **THEN** its plays carry the full asset

#### Scenario: Impossible pace

- **WHEN** a session holds 40 listens in 30 minutes
- **THEN** its plays are flagged as doubtful timing

### Requirement: Tangents are found against a trailing baseline

The lab SHALL place each eligible session on the listener's kept axes and compare it with a baseline from the previous 90 days. It SHALL report a tangent for a qualifying run that returns, and a drift for one that hasn't returned after 45 days. It SHALL report how many sessions it skipped and why.

#### Scenario: A tangent that returns

- **WHEN** sessions leave a stable baseline for two weeks and then return
- **THEN** one tangent is reported with its start, end, peak deviation and the axis that moved most

#### Scenario: A move that stays

- **WHEN** sessions leave the baseline and stay away for 60 days
- **THEN** a drift is reported as not returned, and no tangent is reported for it

#### Scenario: Silence

- **WHEN** a run is followed by 30 days with no usable sessions
- **THEN** it ends marked `gap`, not as a return

#### Scenario: Too little history

- **WHEN** fewer than 10 sessions precede a session within 90 days
- **THEN** that session is skipped as `no_baseline`

### Requirement: The timeline shows tangents as branches

The Tangent timeline SHALL draw tangents leaving and rejoining a trunk, drifts leaving without rejoining, and gaps as gaps. Each branch SHALL show its dates, named axes and top tracks, and SHALL offer its tracks to play where audio exists. It SHALL offer strict, normal and loose presets and state that they are working values.

#### Scenario: Changing a preset

- **WHEN** the listener picks another preset
- **THEN** the branches update to that preset's precomputed result

### Requirement: The lab makes no claim about the listener

Demo text SHALL describe estimated changes in sound. It SHALL NOT state a mood, a cause, a life event or a fact about the listener.

#### Scenario: Demo wording

- **WHEN** the built pages are scanned for claim wording
- **THEN** none is found, and the timeline states that branches are estimates

### Requirement: The listener's verdicts export to a file

Each demo SHALL offer keep, rework and drop with a note, and the home page SHALL export them to one file. The site SHALL work where browser storage is unavailable.

#### Scenario: Exporting verdicts

- **WHEN** the listener marks a demo and exports
- **THEN** the file holds each demo's verdict and note, and no track data
