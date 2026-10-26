# 0007: Audio acquisition via yt-dlp (personal, opt-in)

- Status: accepted
- Date: 2026-10-25

## Context

Audio-first analysis needs full tracks. Spotify previews are unavailable (ADR 0003). The owner chose yt-dlp from YouTube Music, knowing YouTube's terms prohibit downloading and that private copies of streamed tracks are not clearly lawful.

## Decision

`sidetrack audio fetch` is an explicit CLI command, never a scheduled job. Files are stored as `audio/<sha256>.<ext>` on HDD, confirmed with Chromaprint/AcoustID, and recorded in `analysis.audio_assets` with source and video ID. The YouTube cookie file lives outside the repo and is passed by path. Owned files (beets-tagged) and Deezer 30-second previews use the same asset table.

## Consequences

- Audio is never served over HTTP by the web app or API.
- Retention is configurable; derived features survive file deletion.
