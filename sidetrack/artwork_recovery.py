"""One-time operator orchestration through catalog and club public operations."""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from sidetrack.artwork_models import ArtworkRecovery
from sidetrack.catalog import (
    Album,
    album_artwork_target,
    reverse_album_artwork,
    write_album_artwork,
)
from sidetrack.club import (
    SinglesSong,
    reverse_song_artwork,
    song_artwork_target,
    write_song_artwork,
)
from sidetrack.external.artwork import ArtworkError, Discovery, digest, image_url, spotify_entity

READ = {"album": album_artwork_target, "song": song_artwork_target}
WRITE = {"album": write_album_artwork, "song": write_song_artwork}
REVERSE = {"album": reverse_album_artwork, "song": reverse_song_artwork}


def seal(plan: dict) -> dict:
    return {**plan, "digest": digest({k: v for k, v in plan.items() if k != "digest"})}


def validate(plan: dict, kind: str) -> None:
    if plan.get("type") != kind or plan.get("digest") != seal(plan)["digest"]:
        raise ArtworkError("Invalid artwork plan digest or type.")


def inventory(db: Session) -> list[dict]:
    return [
        *[album_artwork_target(db, i) for i in db.scalars(select(Album.id).order_by(Album.id))],
        *[
            song_artwork_target(db, i)
            for i in db.scalars(select(SinglesSong.id).order_by(SinglesSong.id))
        ],
    ]


def preview(targets: list[dict], discovery: Discovery, reviews: dict | None = None) -> dict:
    reviews = reviews or {}
    return seal(
        {
            "type": "artwork-preview",
            "version": 1,
            "entries": [
                discovery.discover(t, reviews.get(t["kind"] + ":" + t["id"]))
                for t in sorted(targets, key=lambda t: (t["kind"], t["id"]))
            ],
        }
    )


def _validate_candidate(entry: dict) -> None:
    image_url(entry["cover_url"])
    provider = entry["provider_url"]
    if provider.startswith("https://musicbrainz.org/release-group/"):
        UUID(provider.removeprefix("https://musicbrainz.org/release-group/"))
    else:
        kind, _ = spotify_entity(provider)
        if kind != ("album" if entry["target"]["kind"] == "album" else "track"):
            raise ArtworkError("Artwork provider kind mismatch.")
    for key in ("image_sha256", "evidence_digest"):
        if not re.fullmatch(r"[a-f0-9]{64}", entry[key]):
            raise ArtworkError("Invalid artwork evidence digest.")
    if not isinstance(entry["bytes"], int) or not 0 < entry["bytes"] <= 5 * 1024 * 1024:
        raise ArtworkError("Invalid artwork evidence size.")


def check(db: Session, plan: dict) -> dict:
    validate(plan, "artwork-preview")
    if db.new or db.dirty or db.deleted:
        raise ArtworkError("Artwork check requires a clean session.")
    entries = []
    seen = set()
    for entry in plan["entries"]:
        if entry["status"] != "ready":
            continue
        target = entry["target"]
        key = (target["kind"], target["id"])
        if key in seen or target["kind"] not in READ:
            raise ArtworkError("Duplicate or invalid artwork target.")
        seen.add(key)
        _validate_candidate(entry)
        current = READ[target["kind"]](db, UUID(target["id"]))
        if current != target or current["cover_url"] or current["recovery_digest"]:
            raise ArtworkError("Artwork target changed after discovery.")
        entries.append(entry)
    return seal(
        {
            "type": "checked-artwork",
            "version": 1,
            "preview_digest": plan["digest"],
            "entries": entries,
        }
    )


def _lock(db: Session, entries: list[dict]) -> None:
    db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('sidetrack:artwork', 0))"))
    for entry in sorted(entries, key=lambda e: (e["target"]["kind"], e["target"]["id"])):
        target = entry["target"]
        try:
            READ[target["kind"]](db, UUID(target["id"]), lock=True)
        except ArtworkError:
            # Verification handles a deleted target; first application rejects it.
            pass
    db.expire_all()


def verify(db: Session, checked: dict) -> dict:
    validate(checked, "checked-artwork")
    receipt = db.get(ArtworkRecovery, checked["digest"])
    if receipt is None or receipt.reversed or receipt.entries != checked["entries"]:
        raise ArtworkError("Active matching artwork receipt not found.")
    mismatches = []
    erased = 0
    for entry in receipt.entries:
        target = entry["target"]
        try:
            current = READ[target["kind"]](db, UUID(target["id"]))
        except ArtworkError:
            erased += 1
            continue
        expected = {
            **target,
            "cover_url": entry["cover_url"],
            "recovery_digest": checked["digest"],
            "recovery_evidence": {
                "cover_url": entry["cover_url"],
                "provider_url": entry["provider_url"],
                "evidence": {k: entry[k] for k in ("evidence_digest", "image_sha256", "bytes")},
            },
        }
        if current != expected:
            mismatches.append({"kind": target["kind"], "id": target["id"]})
    return {
        "verified": not mismatches,
        "mismatches": mismatches,
        "erased": erased,
        "count": len(receipt.entries),
    }


def apply(db: Session, checked: dict, expected_digest: str) -> ArtworkRecovery:
    validate(checked, "checked-artwork")
    if checked["digest"] != expected_digest or db.new or db.dirty or db.deleted:
        raise ArtworkError("Digest mismatch or unclean artwork application session.")
    _lock(db, checked["entries"])
    previous = db.get(ArtworkRecovery, expected_digest)
    if previous:
        if not verify(db, checked)["verified"]:
            raise ArtworkError("Previously recovered artwork changed.")
        return previous
    with db.begin_nested():
        seen = set()
        for entry in checked["entries"]:
            target = entry["target"]
            key = (target["kind"], target["id"])
            if key in seen:
                raise ArtworkError("Duplicate artwork target.")
            seen.add(key)
            _validate_candidate(entry)
            current = READ[target["kind"]](db, UUID(target["id"]))
            if current != target or current["cover_url"] or current["recovery_digest"]:
                raise ArtworkError("Artwork target changed after check.")
        receipt = ArtworkRecovery(plan_digest=expected_digest, entries=checked["entries"])
        db.add(receipt)
        for entry in checked["entries"]:
            target = entry["target"]
            WRITE[target["kind"]](db, UUID(target["id"]), entry, expected_digest)
        db.flush()
    return receipt


def reverse(db: Session, checked: dict, expected_digest: str) -> None:
    if expected_digest != checked.get("digest") or db.new or db.dirty or db.deleted:
        raise ArtworkError("Digest mismatch or unclean artwork reversal session.")
    validate(checked, "checked-artwork")
    _lock(db, checked["entries"])
    receipt = db.get(ArtworkRecovery, expected_digest)
    if receipt and receipt.reversed:
        return
    report = verify(db, checked)
    assert receipt is not None
    if not report["verified"] or report["erased"]:
        raise ArtworkError("Artwork changed or target deleted; review reversal manually.")
    with db.begin_nested():
        for entry in checked["entries"]:
            target = entry["target"]
            REVERSE[target["kind"]](db, UUID(target["id"]))
        receipt.reversed = True
        db.flush()
