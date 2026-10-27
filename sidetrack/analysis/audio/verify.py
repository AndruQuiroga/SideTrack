"""Chromaprint/AcoustID verification of fetched audio against its seed."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Protocol

from sidetrack.types import AudioVerification

CONFIDENT_SCORE = 0.8
TITLE_SIMILARITY = 0.85


class VerifyUnavailable(Exception):
    """Fingerprinting or lookup could not run (no fpcalc, no key, service down)."""


@dataclass(frozen=True)
class Match:
    score: float
    recording_mbid: str
    artist: str
    title: str


@dataclass(frozen=True)
class Verification:
    status: AudioVerification
    score: float | None = None
    recording_mbid: str | None = None
    duration_s: float | None = None
    note: str | None = None


class AcoustIdClient(Protocol):
    def fingerprint(self, path: Path) -> tuple[float, str]: ...

    def lookup(self, duration: float, fingerprint: str) -> list[Match]: ...


_FEAT = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]|\s+(feat\.?|ft\.?|featuring)\s+.*$", re.IGNORECASE)
_NON_WORD = re.compile(r"[^\w\s]")


def normalise(text: str) -> str:
    """Casefold, drop accents, bracketed/featuring clauses and punctuation."""

    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = _FEAT.sub("", text.casefold())
    return " ".join(_NON_WORD.sub(" ", text).split())


_CREDIT_SPLIT = re.compile(
    r"\s*(?:,|&|\+|/|\bx\b|\bfeat\.?|\bft\.?|\bfeaturing\b|\bwith\b)\s*", re.I
)


def credited_artists(text: str) -> set[str]:
    """Each credited name: "A & B feat. C" -> {"a", "b", "c"}. Services often list only one."""

    return {n for part in _CREDIT_SPLIT.split(text) if (n := normalise(part))}


def _same_artist(a: str, b: str) -> bool:
    return a == b or SequenceMatcher(None, a, b).ratio() >= TITLE_SIMILARITY


def matches_seed(match: Match, artist: str, title: str) -> bool:
    """Title must match; any credited artist of the seed must match any credited on the result."""

    seed_credits, match_credits = credited_artists(artist), credited_artists(match.artist)
    artist_ok = any(_same_artist(s, m) for s in seed_credits for m in match_credits)
    title_ok = (
        SequenceMatcher(None, normalise(title), normalise(match.title)).ratio() >= TITLE_SIMILARITY
    )
    return artist_ok and title_ok


def verify(client: AcoustIdClient | None, path: Path, artist: str, title: str) -> Verification:
    """Classify a file as confirmed, mismatch or unverified against the seed it was fetched for."""

    if client is None:
        return Verification(AudioVerification.UNVERIFIED, note="verification not configured")
    try:
        duration, fingerprint = client.fingerprint(path)
    except VerifyUnavailable as exc:
        return Verification(AudioVerification.UNVERIFIED, note=str(exc))
    try:
        matches = client.lookup(duration, fingerprint)
    except VerifyUnavailable as exc:
        return Verification(AudioVerification.UNVERIFIED, duration_s=duration, note=str(exc))

    confident = [m for m in matches if m.score >= CONFIDENT_SCORE]
    if not confident:
        return Verification(AudioVerification.UNVERIFIED, duration_s=duration, note="no match")
    for match in confident:
        if matches_seed(match, artist, title):
            return Verification(
                AudioVerification.CONFIRMED, match.score, match.recording_mbid, duration
            )
    best = max(confident, key=lambda m: m.score)
    return Verification(AudioVerification.MISMATCH, best.score, best.recording_mbid, duration)


class PyAcoustIdClient:
    """AcoustID through pyacoustid (``audio`` extra) and the system ``fpcalc``."""

    def __init__(self, api_key: str | None):
        try:
            import acoustid
        except ImportError as exc:
            raise VerifyUnavailable("pyacoustid is not installed (uv sync --extra audio)") from exc
        self._acoustid = acoustid
        self._api_key = api_key

    def fingerprint(self, path: Path) -> tuple[float, str]:
        try:
            duration, fingerprint = self._acoustid.fingerprint_file(str(path))
        except self._acoustid.FingerprintGenerationError as exc:
            raise VerifyUnavailable(f"fingerprinting failed (is fpcalc installed?): {exc}") from exc
        if isinstance(fingerprint, bytes):
            fingerprint = fingerprint.decode("ascii")
        return float(duration), fingerprint

    def lookup(self, duration: float, fingerprint: str) -> list[Match]:
        if not self._api_key:
            raise VerifyUnavailable("ACOUSTID_API_KEY is not set")
        try:
            response = self._acoustid.lookup(
                self._api_key, fingerprint, int(duration), meta="recordings"
            )
        except self._acoustid.AcoustidError as exc:
            raise VerifyUnavailable(f"AcoustID lookup failed: {exc}") from exc
        if response.get("status") != "ok":
            # AcoustID's error text (e.g. "invalid API key") never contains the key itself.
            message = (response.get("error") or {}).get("message")
            raise VerifyUnavailable(f"AcoustID lookup failed: {message or 'unknown error'}")
        matches = []
        for result in response.get("results", []):
            for recording in result.get("recordings", []):
                artists = ", ".join(a.get("name", "") for a in recording.get("artists", []))
                matches.append(
                    Match(
                        float(result.get("score", 0.0)),
                        recording["id"],
                        artists,
                        recording.get("title", ""),
                    )
                )
        return matches
