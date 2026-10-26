"""Spec: analysis/audio-assets: storage, verification, catalog links, manifest, prune."""

from __future__ import annotations

import csv
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
    export_manifest,
    fetch_seed,
    prune_assets,
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


def test_deezer_search_takes_first_result_with_preview(tmp_path):
    seen = []

    def handler(request):
        seen.append(request.url.path)
        if request.url.path == "/search":
            data = [{"id": 1, "preview": ""}, {"id": 2, "preview": "https://cdn.test/p.mp3"}]
            return httpx.Response(200, json={"data": data})
        return httpx.Response(200, content=b"mp3-bytes")

    download = _deezer(handler).fetch(SEED, tmp_path)

    assert download is not None and download.source_ref == "2"
    assert download.path.read_bytes() == b"mp3-bytes"
    assert seen == ["/search", "/p.mp3"]


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
