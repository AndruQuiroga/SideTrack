"""Spec: analysis/audio-assets: opt-in CLI, redaction, never served or scheduled."""

from __future__ import annotations

import ast
import csv
import io
import json
from pathlib import Path

import pytest
from audio_doubles import FakeAcoustId, fake_sources
from sqlalchemy import func, select

from sidetrack.analysis.audio import Match
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


def test_no_task_fetches_audio(database_url):
    from sidetrack.worker import create_worker_app

    tasks = set(create_worker_app(database_url).tasks)
    assert {t for t in tasks if "procrastinate.builtin_tasks" not in t} == {"sidetrack.execute"}

    allowed = {ROOT / "sidetrack" / "audio.py"}
    package = ROOT / "sidetrack" / "analysis" / "audio"
    for source in (ROOT / "sidetrack").rglob("*.py"):
        if source in allowed or package in source.parents:
            continue
        imports = _imports(source)
        assert not any(m.startswith("sidetrack.analysis.audio") for m in imports), source
        assert not imports & {"yt_dlp", "acoustid", "sidetrack.audio"}, source
    runner = (ROOT / "sidetrack" / "job_runner.py").read_text(encoding="utf-8")
    assert "audio" not in runner


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
