# Spec Delta

## ADDED Requirements

### Requirement: Facet runs measure candidate methods
`audio-lab facets` SHALL run each requested facet method over every asset in a manifest and write a new versioned run directory with one row per asset, facet and method: the output, state, analyzed span, wall-clock and CPU seconds, peak GPU memory when a GPU was used, and the run's hardware and library versions.

#### Scenario: Two methods on a small manifest
- **WHEN** `audio-lab facets` runs two tempo methods over a manifest of 3 assets
- **THEN** the run has 6 tempo rows, each with its output or state, analyzed span and timing, and `run.json` records hardware and versions

#### Scenario: Method cannot load
- **WHEN** a requested facet method's libraries are not installed or its GPU kernels are missing
- **THEN** the method is reported unavailable with its reason, no rows with values are written for it, and the other methods still run

### Requirement: Facet methods declare license records
Every facet adapter SHALL declare its code license, model or data license, runtime dependencies that impose license terms, whether it executes remote repository code, and its pinned revision. A run SHALL copy those declarations into `run.json`, and an adapter without them SHALL NOT run.

#### Scenario: Missing declaration
- **WHEN** an adapter without a weights-license declaration is requested
- **THEN** the command refuses to run it and names the missing field

### Requirement: Facet runs score against reference annotations
When reference annotations are supplied, a facet run SHALL score each method with the facet's stated metric and tolerance: beat F-measure at 70 ms, tempo accuracy allowing and not allowing octave errors, key accuracy with related-key credit stated separately, and boundary hit rate at 0.5 and 3 seconds. Scores SHALL report the number of annotated assets used.

#### Scenario: Beat scoring
- **WHEN** a run scores a tempo method against 30 annotated assets
- **THEN** the report gives beat F-measure at 70 ms and both tempo accuracies, each with n = 30

#### Scenario: No annotations
- **WHEN** a run has no reference annotations for a facet
- **THEN** the report shows the facet's outputs and costs and says it is unscored, without a score

### Requirement: Facet runs test altered audio
A facet run SHALL include, when requested, time-stretched and resampled copies of selected assets at stated rates and report how each method's output changes, so slowed and sped-up edits are measured rather than assumed.

#### Scenario: Slowed copy
- **WHEN** a run includes a copy of an asset resampled to 0.8 times speed
- **THEN** the report lists both tempo outputs and whether the slowed copy's tempo is within 4% of 0.8 times the original's
