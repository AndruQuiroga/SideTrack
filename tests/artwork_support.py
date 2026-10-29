"""Synthetic recovery plans shared by Postgres tests."""

from sidetrack.artwork_recovery import inventory, seal


def ready_plan(db):
    return seal(
        {
            "type": "artwork-preview",
            "version": 1,
            "entries": [
                {
                    "target": t,
                    "status": "ready",
                    "provider_url": (
                        "https://open.spotify.com/"
                        + ("album/" if t["kind"] == "album" else "track/")
                        + "A" * 22
                    ),
                    "cover_url": "https://i.scdn.co/image/synthetic",
                    "image_sha256": "a" * 64,
                    "evidence_digest": "b" * 64,
                    "bytes": 100,
                }
                for t in inventory(db)
                if not t["cover_url"]
            ],
        }
    )
