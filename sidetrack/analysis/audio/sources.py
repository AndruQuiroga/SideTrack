"""Where audio comes from: YouTube Music full tracks and Deezer previews (ADR 0007).

Each source downloads into the audio directory under a temporary name; storage then
moves the file to its content address. A source returns None when it has no result
for a seed and raises SourceError when it fails.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote_plus

import httpx

from sidetrack.types import AudioKind, AudioSource

from .store import partial_path

logger = logging.getLogger(__name__)

MIN_INTERVAL_S = 1.0


@dataclass(frozen=True)
class Seed:
    artist: str
    title: str
    album: str | None = None
    youtube_id: str | None = None
    deezer_id: str | None = None


@dataclass(frozen=True)
class Download:
    path: Path
    ext: str
    source_ref: str


class SourceError(Exception):
    """A source failed for one seed; the run continues."""


class Source(Protocol):
    source: AudioSource
    kind: AudioKind

    def fetch(self, seed: Seed, audio_dir: Path) -> Download | None: ...


class _Throttle:
    def __init__(self, interval: float = MIN_INTERVAL_S):
        self._interval = interval
        self._last = 0.0

    def wait(self) -> None:
        delay = self._last + self._interval - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()


class RedactingLogger:
    """yt-dlp logger that drops any line mentioning a secret path (the cookie file)."""

    def __init__(self, secrets: list[str]):
        self._secrets = [s for s in secrets if s]

    def _emit(self, level: int, message: str) -> None:
        if any(secret in message for secret in self._secrets):
            return
        logger.log(level, "yt-dlp: %s", message)

    def debug(self, message: str) -> None:
        self._emit(logging.DEBUG, message)

    def info(self, message: str) -> None:
        self._emit(logging.DEBUG, message)

    def warning(self, message: str) -> None:
        self._emit(logging.WARNING, message)

    def error(self, message: str) -> None:
        self._emit(logging.ERROR, message)


class YouTubeMusicSource:
    """Full tracks through yt-dlp: native best audio, no transcoding."""

    source = AudioSource.YOUTUBE_MUSIC
    kind = AudioKind.FULL

    def __init__(self, cookies: Path | None = None):
        try:
            import yt_dlp
        except ImportError as exc:
            raise SourceError("yt-dlp is not installed (uv sync --extra audio)") from exc
        self._yt_dlp = yt_dlp
        self._cookies = str(cookies) if cookies else None
        self._throttle = _Throttle()

    def _options(self, **extra: Any) -> dict[str, Any]:
        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "noplaylist": True,
            "logger": RedactingLogger([self._cookies or ""]),
            **extra,
        }
        if self._cookies:
            options["cookiefile"] = self._cookies
        return options

    def _search(self, seed: Seed) -> str | None:
        query = quote_plus(f"{seed.artist} {seed.title}")
        options = self._options(extract_flat="in_playlist", playlistend=1)
        with self._yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(
                f"https://music.youtube.com/search?q={query}#songs", download=False
            )
        for entry in (info or {}).get("entries") or []:
            if entry and entry.get("id"):
                return str(entry["id"])
        return None

    def fetch(self, seed: Seed, audio_dir: Path) -> Download | None:
        self._throttle.wait()
        try:
            video_id = seed.youtube_id or self._search(seed)
            if video_id is None:
                return None
            self._throttle.wait()
            template = str(partial_path(audio_dir, "%(ext)s"))
            options = self._options(format="bestaudio/best", outtmpl=template)
            with self._yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(
                    f"https://music.youtube.com/watch?v={video_id}", download=True
                )
                path = Path(info["requested_downloads"][0]["filepath"])
        except self._yt_dlp.utils.DownloadError as exc:
            raise SourceError(f"yt-dlp failed for {seed.artist} - {seed.title}") from exc
        return Download(
            path=path, ext=str(info.get("ext") or path.suffix.lstrip(".")), source_ref=video_id
        )


class DeezerPreviewSource:
    """30-second MP3 previews from Deezer's public API, downloaded at once (URLs expire)."""

    source = AudioSource.DEEZER_PREVIEW
    kind = AudioKind.PREVIEW
    api = "https://api.deezer.com"

    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(timeout=20.0, follow_redirects=True)
        self._throttle = _Throttle()

    def _get(self, path: str, **params: str) -> dict[str, Any]:
        self._throttle.wait()
        response = self._client.get(f"{self.api}{path}", params=params or None)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    def _find(self, seed: Seed) -> dict[str, Any] | None:
        if seed.deezer_id:
            track = self._get(f"/track/{seed.deezer_id}")
            return None if "error" in track else track
        query = f'artist:"{seed.artist}" track:"{seed.title}"'
        for track in self._get("/search", q=query).get("data", []):
            if track.get("preview"):
                return track
        return None

    def fetch(self, seed: Seed, audio_dir: Path) -> Download | None:
        try:
            track = self._find(seed)
            if track is None or not track.get("preview"):
                return None
            path = partial_path(audio_dir, "mp3")
            self._throttle.wait()
            with self._client.stream("GET", track["preview"]) as response:
                response.raise_for_status()
                with path.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        handle.write(chunk)
        except httpx.HTTPError as exc:
            raise SourceError(f"Deezer failed for {seed.artist} - {seed.title}") from exc
        return Download(path=path, ext="mp3", source_ref=str(track["id"]))
