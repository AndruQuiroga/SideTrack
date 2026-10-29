"""Public catalog interface. Exported ORM models are for cross-domain reads."""

from .artwork import (
    AlbumArtwork,
    album_artwork_target,
    reverse_album_artwork,
    write_album_artwork,
)
from .historical import ensure_historical_album, find_historical_album
from .metadata import (
    enrich_album,
    resolve_album,
    resolve_listen_track,
    upsert_album_from_release_group,
)
from .models import Album, Track

__all__ = [
    "AlbumArtwork",
    "album_artwork_target",
    "write_album_artwork",
    "reverse_album_artwork",
    "find_historical_album",
    "ensure_historical_album",
    "Album",
    "Track",
    "enrich_album",
    "resolve_album",
    "resolve_listen_track",
    "upsert_album_from_release_group",
]
