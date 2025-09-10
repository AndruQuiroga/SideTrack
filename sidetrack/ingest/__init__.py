"""Ingestion backends for external services."""

from .spotify import SpotifyIngester
from .lastfm import LastfmIngester
from .listenbrainz import ListenBrainzIngester

INGESTERS = {
    "spotify": SpotifyIngester,
    "lastfm": LastfmIngester,
    "listenbrainz": ListenBrainzIngester,
}


def get_ingester(name: str):
    """Return an ingester class by name.

    Parameters
    ----------
    name:
        Identifier for the ingester backend (e.g. ``"spotify"``).
    """
    cls = INGESTERS.get(name.lower())
    if not cls:
        raise ValueError(f"Unknown ingester '{name}'")
    return cls()
