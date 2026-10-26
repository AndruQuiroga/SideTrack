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
