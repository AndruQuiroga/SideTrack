# 0005: MusicBrainz mirror on HDD, 40 GB SSD budget

- Status: accepted
- Date: 2026-10-25

## Context

Matching listens and files to recordings via the MusicBrainz web API is limited to 1 request/second (about 4 hours per pass over ~13k songs). The owner's SSD space for this project is about 40 GB; 8 TB of HDD is available.

## Decision

Run the official musicbrainz-docker stack in database-only mode (no search index, ~100 GB) on the HDD, with daily replication. Only batch jobs read it. A nightly `catalog.resolve` job copies the rows Sidetrack needs into its own `catalog` tables on the SSD. Matching is artist-first (trigram over artist names, then exact recording lookup), scored with the old MBIDMapper tiers. Audio files and backups also live on HDD.

## Consequences

- The web app and API never query the mirror directly.
- SSD use is tracked by `scripts/disk_report.py` against the budget.
- Typesense is not used unless trigram matching proves insufficient.
