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
