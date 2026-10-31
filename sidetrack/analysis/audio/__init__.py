"""Audio acquisition for analysis (ADR 0007): explicit CLI only, never scheduled or served.

Nothing here imports yt-dlp or pyacoustid at module load, so images without the
``audio`` extra can import the analysis package.
"""

from .assets import (
    MANIFEST_COLUMNS,
    AssetOutcome,
    ManifestImportPlan,
    ManifestIssue,
    SeedResult,
    apply_manifest_import,
    export_manifest,
    fetch_seed,
    plan_manifest_import,
    prune_assets,
    read_manifest,
    read_seeds,
    resolve_catalog_track,
    reverify_assets,
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
    "ManifestImportPlan",
    "ManifestIssue",
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
    "apply_manifest_import",
    "export_manifest",
    "fetch_seed",
    "plan_manifest_import",
    "prune_assets",
    "read_manifest",
    "read_seeds",
    "resolve_catalog_track",
    "reverify_assets",
]
