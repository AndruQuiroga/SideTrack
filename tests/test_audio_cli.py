"""Spec: analysis/audio-assets: opt-in CLI, redaction, never served or scheduled."""

from __future__ import annotations

import ast
import csv
import hashlib
import io
import json
from pathlib import Path

import pytest
from audio_doubles import FakeAcoustId, fake_sources
from sqlalchemy import func, select

from sidetrack.analysis.audio import MANIFEST_COLUMNS, Match
from sidetrack.analysis.models import AudioAsset
from sidetrack.audio import main
from sidetrack.config import Settings

pytestmark = pytest.mark.unit

ROOT = Path(__file__).parents[1]


def _settings(audio_dir: Path, **overrides) -> Settings:
    values = {"sidetrack_audio_dir": audio_dir, "sidetrack_audio_fetch_enabled": True}
    values.update(overrides)
    return Settings(**values)


def _seeds(tmp_path: Path) -> Path:
    path = tmp_path / "seeds.csv"
    path.write_text("artist,title\nBroadcast,Papercuts\nStereolab,French Disko\n", "utf-8")
    return path


def _run(db, tmp_path, argv, *, settings=None, sources=None, out=None):
    audio_dir = tmp_path / "audio"
    return main(
        argv,
        settings=settings or _settings(audio_dir),
        session=db,
        out=out or io.StringIO(),
        sources_factory=sources or (lambda cookies, only: fake_sources()),
        verifier_factory=lambda s: FakeAcoustId([Match(0.9, "m", "Broadcast", "Papercuts")]),
        resolve_track=lambda session, seed: None,
    )


def test_fetching_is_disabled_by_default(db, tmp_path, capsys):
    audio_dir = tmp_path / "audio"
    settings = _settings(audio_dir, sidetrack_audio_fetch_enabled=False)

    code = _run(db, tmp_path, ["fetch", "--seeds", str(_seeds(tmp_path))], settings=settings)

    assert code == 2
    assert "SIDETRACK_AUDIO_FETCH_ENABLED" in capsys.readouterr().err
    assert not audio_dir.exists()
    assert db.scalar(select(func.count()).select_from(AudioAsset)) == 0


def test_fetch_with_cookies_never_records_them(db, tmp_path, caplog):
    cookies = tmp_path / "private" / "yt-cookies.txt"
    cookies.parent.mkdir()
    cookies.write_text(".youtube.com\tTRUE\t/\tTRUE\t0\tSID\tsecret-cookie-value\n", "utf-8")
    received = []

    def sources(cookie_path, only):
        received.append(cookie_path)
        return fake_sources()

    out = io.StringIO()
    with caplog.at_level("DEBUG"):
        code = _run(
            db,
            tmp_path,
            ["fetch", "--seeds", str(_seeds(tmp_path)), "--cookies", str(cookies)],
            sources=sources,
            out=out,
        )

    assert code == 0
    assert received == [cookies]
    rows = db.scalars(select(AudioAsset)).all()
    assert len(rows) == 4
    recorded = (
        out.getvalue()
        + caplog.text
        + json.dumps(
            [[str(getattr(r, c.name)) for c in AudioAsset.__table__.columns] for r in rows]
        )
    )
    for secret in (str(cookies), cookies.name, "secret-cookie-value"):
        assert secret not in recorded


def test_summary_and_manifest_through_the_cli(db, tmp_path):
    out = io.StringIO()
    assert _run(db, tmp_path, ["fetch", "--seeds", str(_seeds(tmp_path))], out=out) == 0
    assert "Seeds: 2  new assets: 4" in out.getvalue()

    manifest = tmp_path / "manifest.csv"
    assert _run(db, tmp_path, ["manifest", "--out", str(manifest)]) == 0
    rows = list(csv.DictReader(manifest.open(encoding="utf-8")))
    assert len(rows) == 4
    assert all((tmp_path / "audio" / row["path"]).is_file() for row in rows)


def test_prune_requires_retention(db, tmp_path, capsys):
    assert _run(db, tmp_path, ["prune"]) == 2
    assert "SIDETRACK_AUDIO_RETENTION_DAYS" in capsys.readouterr().err


# Audio is never served and never scheduled


def test_no_route_serves_audio(app):
    paths = [getattr(route, "path", "") for route in app.routes]
    assert not [p for p in paths if "audio" in p.lower()]
    schemas = app.openapi()["components"]["schemas"]
    assert not [name for name in schemas if "audio" in name.lower()]
    for name, schema in schemas.items():
        assert not {"sha256", "audio_dir"} & set(schema.get("properties", {})), name


def _imports(source: Path) -> set[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def _manifest(tmp_path: Path, *, count: int = 2, columns=MANIFEST_COLUMNS) -> tuple[Path, Path]:
    """A library of `count` files already on disk, plus its manifest."""

    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, columns, restval="")
        writer.writeheader()
        for index in range(count):
            data = f"audio {index}".encode()
            sha256 = hashlib.sha256(data).hexdigest()
            (audio_dir / f"{sha256}.webm").write_bytes(data)
            writer.writerow(
                {
                    "path": f"{sha256}.webm",
                    "sha256": sha256,
                    "kind": "full",
                    "source": "youtube_music",
                    "source_id": f"video-{index}",
                    "duration_s": "",
                    "verification": "unverified",
                    "track_id": "",
                    "artist": "Broadcast",
                    "title": f"Song {index}",
                }
            )
    return audio_dir, manifest


def _import(db, tmp_path, manifest: Path, *flags: str) -> tuple[int, str]:
    out = io.StringIO()
    code = _run(db, tmp_path, ["import-manifest", "--manifest", str(manifest), *flags], out=out)
    return code, out.getvalue()


def _count_assets(db) -> int:
    return db.scalar(select(func.count()).select_from(AudioAsset))


def test_import_manifest_check(db, tmp_path):
    _, manifest = _manifest(tmp_path)

    code, output = _import(db, tmp_path, manifest)

    assert code == 0
    assert "2 new, 0 existing, 0 rejected, 0 conflicting" in output
    assert "nothing written" in output
    assert _count_assets(db) == 0


def test_import_manifest_apply(db, tmp_path):
    _, manifest = _manifest(tmp_path)

    assert _import(db, tmp_path, manifest, "--apply")[0] == 0
    assert _count_assets(db) == 2

    code, output = _import(db, tmp_path, manifest, "--apply")
    assert code == 0
    assert "0 new, 2 existing" in output
    assert _count_assets(db) == 2


def test_import_manifest_old_columns(db, tmp_path):
    columns = [c for c in MANIFEST_COLUMNS if c not in ("acoustid_score", "recording_mbid")]
    _, manifest = _manifest(tmp_path, columns=columns)

    assert _import(db, tmp_path, manifest, "--apply")[0] == 0
    assert _count_assets(db) == 2


def test_rejected_row_blocks_apply(db, tmp_path):
    audio_dir, manifest = _manifest(tmp_path)
    next(audio_dir.iterdir()).unlink()

    code, output = _import(db, tmp_path, manifest, "--apply")

    assert code == 1
    assert "file is missing" in output
    assert _count_assets(db) == 0


def test_skip_rejected_applies_valid_rows(db, tmp_path):
    audio_dir, manifest = _manifest(tmp_path)
    next(audio_dir.iterdir()).unlink()

    code, output = _import(db, tmp_path, manifest, "--apply", "--skip-rejected")

    assert code == 0
    assert "file is missing" in output
    assert _count_assets(db) == 1


def test_skip_rejected_never_skips_conflicts(db, tmp_path):
    _, manifest = _manifest(tmp_path)
    text = manifest.read_text("utf-8").replace("video-1", "video-0")
    manifest.write_text(text, "utf-8")

    code, output = _import(db, tmp_path, manifest, "--apply", "--skip-rejected")

    assert code == 1
    assert "source belongs to another hash" in output
    assert _count_assets(db) == 0


def test_import_summary_has_no_absolute_paths(db, tmp_path):
    audio_dir, manifest = _manifest(tmp_path)
    next(audio_dir.iterdir()).unlink()

    _, output = _import(db, tmp_path, manifest)

    assert str(tmp_path) not in output


def test_import_manifest_needs_a_readable_manifest(db, tmp_path, capsys):
    (tmp_path / "bad.csv").write_text("path\na.webm\n", "utf-8")

    assert _import(db, tmp_path, tmp_path / "absent.csv")[0] == 2
    assert _import(db, tmp_path, tmp_path / "bad.csv")[0] == 2
    assert "missing columns" in capsys.readouterr().err


def test_embed_queues_imported_assets(db, tmp_path):
    _, manifest = _manifest(tmp_path)
    assert _import(db, tmp_path, manifest, "--apply")[0] == 0
    out = io.StringIO()

    assert _run(db, tmp_path, ["embed"], out=out) == 0

    assert "2 assets" in out.getvalue()


def test_no_task_fetches_audio(database_url):
    from sidetrack.worker import create_worker_app

    tasks = set(create_worker_app(database_url).tasks)
    assert {t for t in tasks if "procrastinate.builtin_tasks" not in t} == {"sidetrack.execute"}
    assert "import_manifest" not in (ROOT / "sidetrack" / "job_runner.py").read_text("utf-8")

    allowed = {ROOT / "sidetrack" / "audio.py"}
    package = ROOT / "sidetrack" / "analysis" / "audio"
    for source in (ROOT / "sidetrack").rglob("*.py"):
        if source in allowed or package in source.parents:
            continue
        imports = _imports(source)
        assert not any(m.startswith("sidetrack.analysis.audio") for m in imports), source
        assert not imports & {"yt_dlp", "acoustid", "sidetrack.audio"}, source
    # The job runner may embed audio (analysis.embed_audio) but never fetches it.
    runner = (ROOT / "sidetrack" / "job_runner.py").read_text(encoding="utf-8")
    assert not any(name in runner for name in ("fetch_seed", "yt_dlp", "acoustid"))


def test_reverify_confirms_without_fetching(db, tmp_path):
    seeds = tmp_path / "one.csv"
    seeds.write_text("artist,title\nBroadcast,Papercuts\n", "utf-8")
    audio_dir = tmp_path / "audio"
    common = {
        "settings": _settings(audio_dir),
        "session": db,
        "resolve_track": lambda session, seed: None,
    }
    calls = []

    def sources(cookies, only):
        calls.append(only)
        return fake_sources()

    main(
        ["fetch", "--seeds", str(seeds)],
        sources_factory=sources,
        verifier_factory=lambda s: FakeAcoustId(unavailable="lookup"),
        out=io.StringIO(),
        **common,
    )
    assert {a.verification.value for a in db.scalars(select(AudioAsset))} == {"unverified"}

    out = io.StringIO()
    confirming = FakeAcoustId([Match(0.9, "mbid-p", "Broadcast", "Papercuts")])
    assert main(["verify"], verifier_factory=lambda s: confirming, out=out, **common) == 0

    assets = db.scalars(select(AudioAsset)).all()
    assert {a.verification.value for a in assets} == {"confirmed"}
    assert {a.recording_mbid for a in assets} == {"mbid-p"}
    assert "2 confirmed" in out.getvalue()
    assert calls == [None]


def test_verify_reports_why_assets_stay_unverified(db, tmp_path):
    seeds = tmp_path / "one.csv"
    seeds.write_text("artist,title\nBroadcast,Papercuts\n", "utf-8")
    common = {
        "settings": _settings(tmp_path / "audio"),
        "session": db,
        "resolve_track": lambda session, seed: None,
        "sources_factory": lambda cookies, only: fake_sources(),
        "verifier_factory": lambda s: FakeAcoustId(unavailable="lookup"),
    }
    main(["fetch", "--seeds", str(seeds)], out=io.StringIO(), **common)

    out = io.StringIO()
    assert main(["verify"], out=out, **common) == 0
    assert "unverified because AcoustID lookup failed: 2" in out.getvalue()


def test_lookup_error_message_is_reported(monkeypatch):
    import types

    from sidetrack.analysis.audio import PyAcoustIdClient, VerifyUnavailable

    fake = types.SimpleNamespace(
        lookup=lambda *a, **k: {
            "status": "error",
            "error": {"code": 4, "message": "invalid API key"},
        },
        AcoustidError=RuntimeError,
        FingerprintGenerationError=RuntimeError,
    )
    monkeypatch.setitem(__import__("sys").modules, "acoustid", fake)
    client = PyAcoustIdClient("not-a-real-key")
    with pytest.raises(VerifyUnavailable, match="invalid API key") as exc:
        client.lookup(10.0, "AQAA")
    assert "not-a-real-key" not in str(exc.value)


# link and coverage: operator commands over catalog tracks (analysis/listen-audio-resolution)


def _link_main(db, argv, out=None):
    out = out or io.StringIO()
    code = main(argv, settings=Settings(database_url="postgresql://unused"), session=db, out=out)
    return code, out.getvalue()


def _track(db, artist, title):
    from sidetrack.catalog import Track

    track = Track(artist_name=artist, title=title)
    db.add(track)
    db.flush()
    return track


def _asset(db, artist, title, **overrides):
    from uuid import uuid4

    from sidetrack.types import AudioKind, AudioSource, AudioVerification

    values = {
        "sha256": uuid4().hex + uuid4().hex,
        "seed_artist": artist,
        "seed_title": title,
        "source": AudioSource.YOUTUBE_MUSIC,
        "source_ref": uuid4().hex,
        "kind": AudioKind.FULL,
        "path": "x.webm",
        "format": "webm",
        "verification": AudioVerification.UNVERIFIED,
    }
    asset = AudioAsset(**{**values, **overrides})
    db.add(asset)
    db.flush()
    return asset


def test_link_prints_exact_counts_per_method(db):
    for index in range(3):
        _track(db, "Artist", f"Song {index}")
        _asset(db, "artist", f"Song {index}")
    _track(db, "Nobody", "Unheard")
    _asset(db, "Stranger", "Unmatched")

    code, text = _link_main(db, ["link"])

    assert code == 0
    assert "seed_identity: 3 (new: 3)" in text
    assert "youtube_id: 0 (new: 0)" in text
    assert "Unlinked assets: 1" in text
    assert "Unlinked tracks: 1" in text

    code, text = _link_main(db, ["link"])
    assert "seed_identity: 3 (new: 0)" in text


def test_manual_reject_and_confirm(db):
    from sidetrack.analysis.models import TrackAudioLink, TrackAudioLinkCorrection

    track = _track(db, "Artist", "Song")
    asset = _asset(db, "Someone Else", "Other")

    code, text = _link_main(db, ["link", "--manual", str(track.id), asset.sha256])
    assert code == 0 and "Manual" in text
    link = db.scalar(select(TrackAudioLink))
    assert (link.method, link.confidence) == ("manual", 1.0)

    link.ambiguous = True
    db.flush()
    assert (
        _link_main(db, ["link", "--confirm", str(track.id), str(asset.id), "--note", "ok"])[0] == 0
    )
    assert db.scalar(select(TrackAudioLink.ambiguous)) is False

    assert _link_main(db, ["link", "--reject", str(track.id), str(asset.id)])[0] == 0
    assert db.scalar(select(func.count()).select_from(TrackAudioLink)) == 0
    assert db.get(TrackAudioLinkCorrection, (track.id, asset.id)).action == "reject"


def test_rejected_link_is_listed_and_not_recreated(db):
    track = _track(db, "Artist", "Song")
    asset = _asset(db, "Artist", "Song")
    _link_main(db, ["link"])
    _link_main(db, ["link", "--reject", str(track.id), str(asset.id)])

    code, text = _link_main(db, ["link"])

    assert "Rejected pairs skipped: 1" in text
    assert f"rejected track {track.id} asset {asset.id}" in text
    assert "seed_identity: 0 (new: 0)" in text


def test_link_with_unknown_asset_or_bad_track_writes_nothing(db, capsys):
    track = _track(db, "Artist", "Song")

    assert _link_main(db, ["link", "--manual", str(track.id), "nope"])[0] == 1
    assert _link_main(db, ["link", "--manual", "not-a-uuid", "nope"])[0] == 1

    err = capsys.readouterr().err
    assert "No asset nope" in err and "Not a track ID" in err


def test_link_queue_defers_a_default_queue_job(db):
    from sqlalchemy import text

    from sidetrack.queue_models import BackgroundJob

    code, output = _link_main(db, ["link", "--queue"])

    job = db.scalar(select(BackgroundJob).where(BackgroundJob.task == "analysis.link_audio"))
    assert code == 0 and str(job.id) in output
    queue = db.scalar(
        text("SELECT queue_name FROM job_queue.procrastinate_jobs WHERE id = :id"),
        {"id": job.queue_job_id},
    )
    assert queue == "default"
    assert db.scalar(select(func.count()).select_from(AudioAsset)) == 0


def test_nothing_schedules_the_link_task(db):
    from sidetrack.queue_maintenance import seed_cleanup
    from sidetrack.queue_models import JobSchedule

    seed_cleanup(db)
    assert db.scalars(select(JobSchedule).where(JobSchedule.task.like("%link_audio%"))).all() == []
    allowed = {"audio.py", "job_runner.py", "links.py", "__init__.py"}
    for source in (ROOT / "sidetrack").rglob("*.py"):
        if source.name not in allowed:
            assert "link_audio" not in source.read_text("utf-8"), source


def test_coverage_prints_counts_and_reasons(db):
    from datetime import UTC, datetime, timedelta

    from test_audio_embeddings_neighbours import embed

    from sidetrack.analysis.models import TrackAudioLink
    from sidetrack.identity import User
    from sidetrack.listening import ListenEvent, ListenSource, sessionize

    user = User(display_name="Listener", timezone="UTC")
    db.add(user)
    db.flush()
    heard = _track(db, "Artist", "Heard")
    bare = _track(db, "Artist", "Bare")
    asset = _asset(db, "Artist", "Heard")
    db.add(
        TrackAudioLink(
            track_id=heard.id,
            asset_id=asset.id,
            method="manual",
            confidence=1.0,
            matcher_version="links-v1",
        )
    )
    embed(db, asset, [1.0, 0.0])
    now = datetime.now(UTC)
    for index, track in enumerate([heard] * 3 + [bare]):
        db.add(
            ListenEvent(
                user_id=user.id,
                track_id=track.id,
                played_at=now - timedelta(days=2, hours=index),
                source=ListenSource.LISTENBRAINZ,
            )
        )
    db.flush()
    sessionize(db, user.id)

    code, text = _link_main(db, ["coverage", "--user", str(user.id), "--weeks", "4"])

    assert code == 0
    assert "Included plays: 4, with audio: 3 (75.0%)" in text
    assert "no_link: 1" in text and "no_embedding: 0" in text


def test_coverage_with_no_plays_invents_no_share(db):
    from sidetrack.identity import User

    user = User(display_name="Quiet")
    db.add(user)
    db.flush()

    code, text = _link_main(db, ["coverage", "--user", str(user.id)])

    assert code == 0 and "no plays" in text and "%" not in text
    assert _link_main(db, ["coverage", "--user", str(user.id), "--weeks", "0"])[0] == 2


def test_link_job_runs_in_the_job_runner(engine, monkeypatch):
    from sqlalchemy import delete, text
    from sqlalchemy.orm import Session

    from sidetrack import db as database
    from sidetrack.analysis.models import TrackAudioLink
    from sidetrack.catalog import Track
    from sidetrack.job_runner import run
    from sidetrack.queue_client import enqueue
    from sidetrack.queue_models import BackgroundJob

    monkeypatch.setattr(database, "_engine", engine)
    with Session(engine) as writer:
        track = _track(writer, "Runner Artist", "Runner Song")
        asset = _asset(writer, "runner artist", "Runner Song")
        job = enqueue(writer, "analysis.link_audio", {})
        ids = track.id, asset.id, job.id, job.queue_job_id
        writer.commit()
    track_id, asset_id, job_id, queue_id = ids
    try:
        assert run(job_id) == 0
        with Session(engine) as reader:
            result = reader.get(BackgroundJob, job_id)
            assert result.status == "finished"
            assert result.result["created"]["seed_identity"] >= 1
            links = reader.scalars(
                select(TrackAudioLink).where(TrackAudioLink.track_id == track_id)
            ).all()
            assert [(row.asset_id, row.method) for row in links] == [(asset_id, "seed_identity")]
    finally:
        with Session(engine) as cleanup:
            cleanup.execute(text("SET LOCAL search_path TO job_queue,public"))
            cleanup.execute(text("DELETE FROM procrastinate_jobs WHERE id=:id"), {"id": queue_id})
            cleanup.execute(text("DELETE FROM background_jobs WHERE id=:id"), {"id": job_id})
            cleanup.execute(delete(AudioAsset).where(AudioAsset.id == asset_id))
            cleanup.execute(delete(Track).where(Track.id == track_id))
            cleanup.commit()
