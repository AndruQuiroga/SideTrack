"""Test doubles for audio sources and AcoustID. Never used outside tests."""

from __future__ import annotations

from pathlib import Path

from sidetrack.analysis.audio import Download, Match, Seed, SourceError, VerifyUnavailable
from sidetrack.analysis.audio.store import partial_path
from sidetrack.types import AudioKind, AudioSource


class FakeSource:
    """Writes deterministic bytes per seed; ``missing`` seeds return no result."""

    def __init__(self, source: AudioSource, kind: AudioKind, *, missing=(), failing=()):
        self.source, self.kind = source, kind
        self.missing, self.failing = set(missing), set(failing)
        self.calls: list[Seed] = []

    def payload(self, seed: Seed) -> bytes:
        return f"{self.source.value}:{seed.artist}:{seed.title}".encode() * 64

    def fetch(self, seed: Seed, audio_dir: Path) -> Download | None:
        self.calls.append(seed)
        if seed.title in self.failing:
            raise SourceError(f"{self.source.value} failed")
        if seed.title in self.missing:
            return None
        ext = "webm" if self.kind is AudioKind.FULL else "mp3"
        path = partial_path(audio_dir, ext)
        path.write_bytes(self.payload(seed))
        ref = seed.youtube_id or seed.deezer_id or f"{self.source.value}-{seed.title}"
        return Download(path=path, ext=ext, source_ref=ref)


def fake_sources(**kwargs) -> list[FakeSource]:
    return [
        FakeSource(AudioSource.YOUTUBE_MUSIC, AudioKind.FULL, **kwargs.get("full", {})),
        FakeSource(AudioSource.DEEZER_PREVIEW, AudioKind.PREVIEW, **kwargs.get("preview", {})),
    ]


class FakeAcoustId:
    """Returns the configured matches; ``unavailable`` simulates fpcalc or service failure."""

    def __init__(self, matches: list[Match] | None = None, *, unavailable: str | None = None):
        self.matches = matches or []
        self.unavailable = unavailable

    def fingerprint(self, path: Path) -> tuple[float, str]:
        if self.unavailable == "fpcalc":
            raise VerifyUnavailable("fingerprinting failed (is fpcalc installed?)")
        return 212.5, "AQAA-fake-fingerprint"

    def lookup(self, duration: float, fingerprint: str) -> list[Match]:
        if self.unavailable == "lookup":
            raise VerifyUnavailable("AcoustID lookup failed")
        return self.matches
