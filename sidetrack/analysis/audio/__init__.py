"""Audio acquisition for analysis (ADR 0007): explicit CLI only, never scheduled or served.

Nothing here imports yt-dlp or pyacoustid at module load, so images without the
``audio`` extra can import the analysis package.
"""

from .assets import (
    MANIFEST_COLUMNS,
    AssetOutcome,
    SeedResult,
    export_manifest,
    fetch_seed,
    prune_assets,
    read_seeds,
    resolve_catalog_track,
)
from .sources import (
    DeezerPreviewSource,
    Download,
    Seed,
    Source,
    SourceError,
    YouTubeMusicSource,
)
from .verify import AcoustIdClient, Match, PyAcoustIdClient, Verification, VerifyUnavailable

__all__ = [
    "MANIFEST_COLUMNS",
    "AcoustIdClient",
    "AssetOutcome",
    "DeezerPreviewSource",
    "Download",
    "Match",
    "PyAcoustIdClient",
    "Seed",
    "SeedResult",
    "Source",
    "SourceError",
    "Verification",
    "VerifyUnavailable",
    "YouTubeMusicSource",
    "export_manifest",
    "fetch_seed",
    "prune_assets",
    "read_seeds",
    "resolve_catalog_track",
]
