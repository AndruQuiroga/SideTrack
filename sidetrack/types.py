"""Shared provider identifiers; independent of ORM initialization."""

from enum import Enum


class ProviderType(str, Enum):
    DISCORD = "discord"
    SPOTIFY = "spotify"
    LASTFM = "lastfm"
    LISTENBRAINZ = "listenbrainz"


class ListenSource(str, Enum):
    SPOTIFY = "spotify"
    LASTFM = "lastfm"
    LISTENBRAINZ = "listenbrainz"
    MANUAL = "manual"


class ClubRole(str, Enum):
    MEMBER = "member"
    ADMIN = "admin"


class ListeningVisibility(str, Enum):
    """Who besides the owner may see a user's listening data (ADR 0009)."""

    PRIVATE = "private"
    CLUB = "club"


class AudioSource(str, Enum):
    """Where an audio asset came from (ADR 0007)."""

    YOUTUBE_MUSIC = "youtube_music"
    DEEZER_PREVIEW = "deezer_preview"


class AudioKind(str, Enum):
    FULL = "full"
    PREVIEW = "preview"


class AudioVerification(str, Enum):
    """Whether a Chromaprint/AcoustID match confirms the requested track."""

    CONFIRMED = "confirmed"
    MISMATCH = "mismatch"
    UNVERIFIED = "unverified"
