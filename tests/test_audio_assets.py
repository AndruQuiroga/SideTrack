"""Spec: analysis/audio-assets: storage, verification, catalog links, manifest, prune."""

from __future__ import annotations

import csv
import hashlib
import io
import sys
import types
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from audio_doubles import FakeAcoustId, fake_sources
from sqlalchemy import func, select

from sidetrack.analysis.audio import (
    DeezerPreviewSource,
    Match,
    Seed,
    apply_manifest_import,
    export_manifest,
    fetch_seed,
    plan_manifest_import,
    prune_assets,
    read_manifest,
    read_seeds,
)
from sidetrack.analysis.audio.sources import RedactingLogger
from sidetrack.analysis.audio.verify import matches_seed, normalise
from sidetrack.analysis.models import AudioAsset
from sidetrack.types import AudioKind, AudioSource, AudioVerification

pytestmark = pytest.mark.unit

SEED = Seed(artist="Broadcast", title="Come On Let's Go")
CONFIRMING = [Match(0.95, "mbid-1", "Broadcast", "Come On Let's Go")]


def _no_track(db, seed):
    return None


def _fetch(db, tmp_path, seed=SEED, *, sources=None, verifier=None, resolve=_no_track):
    return fetch_seed(
        db,
        seed,
        audio_dir=tmp_path,
        sources=sources if sources is not None else fake_sources(),
        verifier=verifier if verifier is not None else FakeAcoustId(CONFIRMING),
        resolve_track=resolve,
    )


def _assets(db):
    return db.scalars(select(AudioAsset).order_by(AudioAsset.kind)).all()


def _files(tmp_path):
    return sorted(p.name for p in tmp_path.iterdir() if not p.name.startswith("."))


# Seeds fetch full tracks and previews


def test_both_sources_found(db, tmp_path):
    result = _fetch(db, tmp_path)

    assert result.missing == []
    full, preview = _assets(db)
    assert (full.kind, full.source) == (AudioKind.FULL, AudioSource.YOUTUBE_MUSIC)
    assert (preview.kind, preview.source) == (AudioKind.PREVIEW, AudioSource.DEEZER_PREVIEW)
    assert full.source_ref and preview.source_ref
    assert len(_files(tmp_path)) == 2


def test_source_has_no_result_continues(db, tmp_path):
    sources = fake_sources(preview={"missing": {SEED.title}})
    next_seed = Seed(artist="Stereolab", title="French Disko")

    first = _fetch(db, tmp_path, sources=sources)
    second = _fetch(db, tmp_path, next_seed, sources=sources)

    assert [a.kind for a in first.assets] == [AudioKind.FULL]
    assert first.missing == [(AudioSource.DEEZER_PREVIEW, "no result")]
    assert len(second.assets) == 2


def test_source_error_is_reported_per_seed(db, tmp_path):
    result = _fetch(db, tmp_path, sources=fake_sources(full={"failing": {SEED.title}}))
    assert [a.kind for a in result.assets] == [AudioKind.PREVIEW]
    assert result.missing[0][0] is AudioSource.YOUTUBE_MUSIC


def test_explicit_video_id_skips_search(tmp_path, monkeypatch):
    calls: list[str] = []

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download):
            calls.append(url)
            target = tmp_path / "dl.webm"
            target.write_bytes(b"audio")
            return {"ext": "webm", "requested_downloads": [{"filepath": str(target)}]}

    fake = types.ModuleType("yt_dlp")
    fake.YoutubeDL = FakeYoutubeDL
    fake.utils = types.SimpleNamespace(DownloadError=RuntimeError)
    monkeypatch.setitem(sys.modules, "yt_dlp", fake)
    from sidetrack.analysis.audio import YouTubeMusicSource

    source = YouTubeMusicSource()
    source._throttle.wait = lambda: None
    download = source.fetch(Seed("A", "B", youtube_id="abc123XYZ00"), tmp_path)

    assert download is not None and download.source_ref == "abc123XYZ00"
    assert calls == ["https://music.youtube.com/watch?v=abc123XYZ00"]


def _deezer(handler) -> DeezerPreviewSource:
    source = DeezerPreviewSource(httpx.Client(transport=httpx.MockTransport(handler)))
    source._throttle.wait = lambda: None
    return source


def _deezer_track(track_id, artist, title, preview="https://cdn.test/p.mp3"):
    return {"id": track_id, "artist": {"name": artist}, "title": title, "preview": preview}


def test_deezer_search_takes_first_matching_result_with_preview(tmp_path):
    seen = []

    def handler(request):
        seen.append((request.url.path, request.url.params.get("q")))
        if request.url.path == "/search":
            data = [
                _deezer_track(1, "Broadcast", "Come On Let's Go", preview=""),
                _deezer_track(2, "A Tribute Band", "Come On Let's Go"),
                _deezer_track(3, "Broadcast", "Come On Let's Go (Remastered)"),
            ]
            return httpx.Response(200, json={"data": data})
        return httpx.Response(200, content=b"mp3-bytes")

    download = _deezer(handler).fetch(SEED, tmp_path)

    assert download is not None and download.source_ref == "3"
    assert download.path.read_bytes() == b"mp3-bytes"
    assert seen == [("/search", "Broadcast Come On Let's Go"), ("/p.mp3", None)]


def test_deezer_search_without_matching_artist_is_no_result(tmp_path):
    def handler(request):
        data = [_deezer_track(9, "Someone Else", "Come On Let's Go")]
        return httpx.Response(200, json={"data": data})

    assert _deezer(handler).fetch(SEED, tmp_path) is None


def test_deezer_explicit_id_and_no_preview(tmp_path):
    def handler(request):
        assert request.url.path == "/track/42"
        return httpx.Response(200, json={"id": 42, "preview": ""})

    assert _deezer(handler).fetch(Seed("A", "B", deezer_id="42"), tmp_path) is None


# Files are stored once by content hash


def test_same_audio_stored_once(db, tmp_path):
    first = _fetch(db, tmp_path)
    second = _fetch(db, tmp_path)

    assert db.scalar(select(func.count()).select_from(AudioAsset)) == 2
    assert len(_files(tmp_path)) == 2
    assert not any(a.already_stored for a in first.assets)
    assert all(a.already_stored for a in second.assets)
    for asset in _assets(db):
        assert asset.path == f"{asset.sha256}.{asset.format}"
        assert (tmp_path / asset.path).is_file()


# Assets are verified by fingerprint


def test_matching_recording_is_confirmed(db, tmp_path):
    _fetch(db, tmp_path, verifier=FakeAcoustId(CONFIRMING))
    for asset in _assets(db):
        assert asset.verification is AudioVerification.CONFIRMED
        assert asset.recording_mbid == "mbid-1"
        assert asset.duration_s == 212.5


def test_wrong_upload_is_mismatch(db, tmp_path):
    wrong = [Match(0.97, "mbid-cover", "Some Cover Band", "Come On Let's Go")]
    result = _fetch(db, tmp_path, verifier=FakeAcoustId(wrong))
    assert {a.verification for a in result.assets} == {AudioVerification.MISMATCH}
    assert all(a.recording_mbid == "mbid-cover" for a in _assets(db))


@pytest.mark.parametrize("unavailable", ["fpcalc", "lookup"])
def test_acoustid_unavailable_is_unverified(db, tmp_path, unavailable):
    result = _fetch(db, tmp_path, verifier=FakeAcoustId(unavailable=unavailable))
    assert {a.verification for a in result.assets} == {AudioVerification.UNVERIFIED}
    assert all(a.note for a in result.assets)
    assert len(_files(tmp_path)) == 2


def test_low_score_is_unverified(db, tmp_path):
    weak = [Match(0.4, "mbid-1", "Broadcast", "Come On Let's Go")]
    result = _fetch(db, tmp_path, verifier=FakeAcoustId(weak))
    assert {a.verification for a in result.assets} == {AudioVerification.UNVERIFIED}


def test_title_normalisation():
    assert normalise("Café (Remastered 2011) feat. Someone") == "cafe"
    assert matches_seed(Match(0.9, "m", "Broadcast feat. X", "Come on, let's go!"), *SEED_PAIR)
    assert not matches_seed(Match(0.9, "m", "Broadcast", "Tears in the Typing Pool"), *SEED_PAIR)


SEED_PAIR = (SEED.artist, SEED.title)


# Assets link to the catalog when possible


def test_obscure_track_not_in_musicbrainz(db, tmp_path):
    _fetch(db, tmp_path, resolve=_no_track)
    for asset in _assets(db):
        assert asset.track_id is None
        assert (asset.seed_artist, asset.seed_title) == (SEED.artist, SEED.title)


def test_resolved_track_is_linked_once_per_seed(db, tmp_path):
    from sidetrack.catalog import Album, Track

    album = Album(title="Haha Sound", artist_name="Broadcast")
    db.add(album)
    db.flush()
    track = Track(album_id=album.id, title=SEED.title, artist_name=SEED.artist)
    db.add(track)
    db.flush()
    calls = []

    def resolve(session, seed):
        calls.append(seed)
        return track.id

    _fetch(db, tmp_path, resolve=resolve)
    assert {a.track_id for a in _assets(db)} == {track.id}
    assert len(calls) == 1


# The manifest exports assets for analysis


def test_manifest_lists_existing_files(db, tmp_path):
    for title in ("One", "Two", "Three"):
        _fetch(db, tmp_path, Seed("Band", title))
    out = io.StringIO()

    assert export_manifest(db, tmp_path, out) == 6
    rows = list(csv.DictReader(io.StringIO(out.getvalue())))
    assert len(rows) == 6
    assert all((tmp_path / row["path"]).is_file() for row in rows)
    assert {row["kind"] for row in rows} == {"full", "preview"}

    (tmp_path / rows[0]["path"]).unlink()
    assert export_manifest(db, tmp_path, io.StringIO()) == 5


def test_manifest_includes_verification_detail(db, tmp_path):
    verifier = FakeAcoustId([Match(0.97, "mbid-1", SEED.artist, SEED.title)])
    _fetch(db, tmp_path, verifier=verifier)
    out = io.StringIO()
    export_manifest(db, tmp_path, out)

    confirmed = [
        row
        for row in csv.DictReader(io.StringIO(out.getvalue()))
        if row["verification"] == "confirmed"
    ]
    assert confirmed
    assert {row["recording_mbid"] for row in confirmed} == {"mbid-1"}
    assert {float(row["acoustid_score"]) for row in confirmed} == {0.97}


def _library(tmp_path, count=2):
    """Files and manifest rows for a library that this database has never seen."""

    audio_dir = tmp_path / "library"
    audio_dir.mkdir()
    rows = []
    for index in range(count):
        data = f"audio {index}".encode()
        sha256 = hashlib.sha256(data).hexdigest()
        (audio_dir / f"{sha256}.webm").write_bytes(data)
        rows.append(
            {
                "path": f"{sha256}.webm",
                "sha256": sha256,
                "kind": "full",
                "source": "youtube_music",
                "source_id": f"video-{index}",
                "duration_s": "180.50",
                "verification": "unverified",
                "track_id": "",
                "artist": "Broadcast",
                "title": f"Song {index}",
            }
        )
    return audio_dir, rows


def _import(db, audio_dir, rows):
    plan = plan_manifest_import(db, audio_dir, rows)
    apply_manifest_import(db, plan)
    return plan


def _asset_count(db):
    return db.scalar(select(func.count()).select_from(AudioAsset))


def test_import_check_writes_nothing(db, tmp_path):
    audio_dir, rows = _library(tmp_path)

    plan = plan_manifest_import(db, audio_dir, rows)

    assert (len(plan.new), plan.existing, plan.rejected, plan.conflicts) == (2, 0, [], [])
    assert _asset_count(db) == 0


def test_import_rejects_missing_file(db, tmp_path):
    audio_dir, rows = _library(tmp_path)
    (audio_dir / rows[0]["path"]).unlink()

    plan = plan_manifest_import(db, audio_dir, rows)

    assert [(i.path, i.reason) for i in plan.rejected] == [(rows[0]["path"], "file is missing")]
    assert len(plan.new) == 1


def test_import_rejects_hash_mismatch(db, tmp_path):
    audio_dir, rows = _library(tmp_path)
    file = audio_dir / rows[0]["path"]
    file.write_bytes(b"something else")

    plan = plan_manifest_import(db, audio_dir, rows)

    assert [i.reason for i in plan.rejected] == ["file does not match its hash"]
    assert file.read_bytes() == b"something else"


@pytest.mark.parametrize("path", ["other.webm", "../outside.webm", "/etc/passwd"])
def test_import_rejects_path_not_named_by_hash(db, tmp_path, path):
    audio_dir, rows = _library(tmp_path, 1)
    rows[0]["path"] = path

    plan = plan_manifest_import(db, audio_dir, rows)

    assert [i.reason for i in plan.rejected] == ["file name does not match its hash"]


def test_import_rejects_invalid_value(db, tmp_path):
    audio_dir, rows = _library(tmp_path, 1)
    rows[0]["kind"] = "bootleg"

    plan = plan_manifest_import(db, audio_dir, rows)

    assert [i.reason for i in plan.rejected] == ["row has an invalid value"]


def test_import_rejects_mismatched_asset(db, tmp_path):
    audio_dir, rows = _library(tmp_path, 1)
    rows[0]["verification"] = "mismatch"

    plan = plan_manifest_import(db, audio_dir, rows)

    assert [i.reason for i in plan.rejected] == ["verification is mismatch"]


def test_import_reports_conflict(db, tmp_path):
    audio_dir, rows = _library(tmp_path)
    _import(db, audio_dir, rows[:1])
    rows[1]["source_id"] = rows[0]["source_id"]

    plan = plan_manifest_import(db, audio_dir, rows)

    assert plan.existing == 1
    assert [i.reason for i in plan.conflicts] == ["source belongs to another hash"]

    rows[1]["source_id"], rows[1]["sha256"] = "other-video", rows[0]["sha256"]
    plan = plan_manifest_import(db, audio_dir, rows[1:])
    assert [i.reason for i in plan.conflicts] == ["hash belongs to another source"]


def test_import_creates_assets(db, tmp_path):
    audio_dir, rows = _library(tmp_path)
    rows[0]["acoustid_score"], rows[0]["recording_mbid"] = "0.91", "mbid-1"

    _import(db, audio_dir, rows)

    asset = db.scalar(select(AudioAsset).where(AudioAsset.sha256 == rows[0]["sha256"]))
    assert asset.source is AudioSource.YOUTUBE_MUSIC
    assert asset.source_ref == "video-0"
    assert asset.kind is AudioKind.FULL
    assert asset.path == rows[0]["path"]
    assert asset.format == "webm"
    assert asset.duration_s == 180.5
    assert asset.verification is AudioVerification.UNVERIFIED
    assert (asset.seed_artist, asset.seed_title) == ("Broadcast", "Song 0")
    assert (asset.acoustid_score, asset.recording_mbid) == (0.91, "mbid-1")
    assert asset.fetched_at.date() == datetime.now(UTC).date()
    assert _asset_count(db) == 2


def test_import_drops_track_link(db, tmp_path):
    audio_dir, rows = _library(tmp_path, 1)
    rows[0]["track_id"] = str(uuid4())

    _import(db, audio_dir, rows)

    assert db.scalar(select(AudioAsset.track_id)) is None


def test_import_retry_adds_nothing(db, tmp_path):
    audio_dir, rows = _library(tmp_path)
    _import(db, audio_dir, rows)

    plan = _import(db, audio_dir, rows)

    assert (plan.new, plan.existing, plan.rejected, plan.conflicts) == ([], 2, [], [])
    assert _asset_count(db) == 2


def test_read_manifest_requires_columns():
    with pytest.raises(ValueError, match="sha256"):
        read_manifest(io.StringIO("path,kind\na.webm,full\n"))


def test_read_seeds_requires_columns():
    seeds = read_seeds(io.StringIO("artist,title,youtube_id\nA,B,vid\n,skipped,\n"))
    assert seeds == [Seed("A", "B", youtube_id="vid")]
    with pytest.raises(ValueError):
        read_seeds(io.StringIO("name\nx\n"))


# Pruning removes files and keeps records


def test_prune_expired_file(db, tmp_path):
    _fetch(db, tmp_path)
    old, recent = _assets(db)
    now = datetime.now(UTC)
    old.fetched_at = now - timedelta(days=31)
    db.flush()

    assert prune_assets(db, tmp_path, 30, now=now) == 1

    assert not (tmp_path / old.path).exists()
    assert (tmp_path / recent.path).exists()
    assert db.get(AudioAsset, old.id).file_deleted_at == now
    out = io.StringIO()
    assert export_manifest(db, tmp_path, out) == 1
    assert old.path not in out.getvalue()


def test_redacting_logger_drops_secret_lines(caplog):
    secret = f"C:/Users/someone/cookies-{uuid4().hex}.txt"
    log = RedactingLogger([secret])
    with caplog.at_level("DEBUG"):
        log.warning(f"Loading cookies from {secret}")
        log.warning("ordinary message")
    assert secret not in caplog.text
    assert "ordinary message" in caplog.text


@pytest.mark.parametrize(
    ("seed_artist", "result_artist", "expected"),
    [
        ("ILLENIUM & WYLDE", "ILLENIUM", True),  # Deezer lists the primary artist only
        ("Dabin, William Black & Audra Miller", "William Black", True),
        ("Dabin feat Dia Frampton", "Dabin", True),
        ("Trivecta & MitiS", "MitiS, Trivecta", True),
        ("ILLENIUM & WYLDE", "Some Cover Band", False),
    ],
)
def test_collaboration_credits_match(seed_artist, result_artist, expected):
    assert matches_seed(Match(0.9, "m", result_artist, "Ur Alive"), seed_artist, "Ur Alive") is (
        expected
    )
