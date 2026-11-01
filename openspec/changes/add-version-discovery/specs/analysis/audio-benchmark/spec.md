# Spec Delta

## ADDED Requirements

### Requirement: Version runs score methods on altered audio
`audio-lab versions` SHALL score each candidate version method on pairs made by altering manifest assets: pitch-preserving time-stretch, resampled speed change (pitch moves with tempo), trimming and re-encoding, each at stated levels. It SHALL report retrieval rate per transform and level with n, and record failures and out-of-memory errors as unavailable, never as misses.

#### Scenario: Speed change reported per level
- **WHEN** a version run applies resampled speed changes of 0.8x, 0.9x, 1.1x and 1.25x to 50 assets
- **THEN** the report lists each method's retrieval rate at each level with n = 50, separately from pitch-preserving stretches

#### Scenario: Method cannot run
- **WHEN** a method's model does not fit in GPU memory
- **THEN** the run records that method as unavailable with the error and reports no rates for it

### Requirement: Version runs report false candidates on hard negatives
A version run SHALL report each method's false-candidate rate on hard negatives: pairs of different songs by the same artist and pairs that are close MuQ-MuLan neighbours, with n and the threshold used.

#### Scenario: Same-artist negatives
- **WHEN** a version run includes 100 same-artist different-song pairs
- **THEN** the report gives each method's share of those pairs scored above its threshold, with n = 100

### Requirement: Version methods declare license and dependency records
Each version method in audio-lab SHALL declare the licenses of its code, weights and training data, its dependencies and pinned revisions, and whether it loads repository-supplied code. A method with an unreviewed record SHALL be marked not eligible for production in every report.

#### Scenario: Unreviewed method
- **WHEN** a version run includes a method whose weight license is unreviewed
- **THEN** the report shows its scores marked not eligible for production with the missing review named

### Requirement: Version run outputs stay outside the repository
`audio-lab versions` SHALL refuse an output path inside the repository, and SHALL keep altered audio only in its run directory, never serving it over HTTP.

#### Scenario: Output inside repository
- **WHEN** the operator passes an output path inside the repository
- **THEN** the command exits with an error and writes nothing
