"""Spec: analysis/listening-lab: the local site, its home page and its verdict export."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from audio_lab.cli import main
from audio_lab.lab.site import Demo, LabContext, build_site
from audio_lab.seeds import OutputInRepo, repo_root

NEEDLE = "zorptone artist"  # stands in for track data that must never reach the verdict file


def needs_snapshot(context: LabContext) -> dict:
    context.require(snapshot="the listening snapshot")
    return {"rows": 3}


def always(context: LabContext) -> dict:
    return {"artist": NEEDLE, "audio": Path("/music/a.wav").as_uri()}


def demos() -> list[Demo]:
    body = "<div id='x'>demo body</div>"
    return [
        Demo("needy", "Needy", "Needs the snapshot.", needs_snapshot, body),
        Demo("plain", "Plain", "Needs nothing.", always, body),
    ]


def test_missing_input_is_unavailable(tmp_path):
    out = tmp_path / "lab"
    entries = build_site(out, LabContext(), demos())
    needy = next(e for e in entries if e["name"] == "needy")
    assert needy["status"] == "unavailable"
    assert "snapshot" in needy["reason"]
    assert not (out / "needy.html").exists()
    assert "listening snapshot was not given" in (out / "index.html").read_text(encoding="utf-8")


def test_other_demos_still_build(tmp_path):
    out = tmp_path / "lab"
    entries = build_site(out, LabContext(snapshot=tmp_path / "nope.csv"), demos())
    assert [(e["name"], e["status"]) for e in entries] == [
        ("needy", "unavailable"),
        ("plain", "ready"),
    ]
    assert "not found at" in entries[0]["reason"]
    assert NEEDLE in (out / "plain.html").read_text(encoding="utf-8")


def test_stale_page_is_removed_when_a_demo_becomes_unavailable(tmp_path):
    out = tmp_path / "lab"
    snapshot = tmp_path / "snap.csv"
    snapshot.write_text("x", encoding="utf-8")
    build_site(out, LabContext(snapshot=snapshot), demos())
    assert (out / "needy.html").exists()
    build_site(out, LabContext(), demos())
    assert not (out / "needy.html").exists()


def test_output_refused_in_repo():
    root = repo_root(Path(__file__).resolve())
    target = root / "lab-out-should-not-exist"
    with pytest.raises(OutputInRepo):
        build_site(target, LabContext(), demos())
    assert not target.exists()
    assert main(["lab", "build", "--out", str(target)]) == 1
    assert not target.exists()


def test_build_command(tmp_path, capsys):
    out = tmp_path / "lab"
    assert main(["lab", "build", "--out", str(out)]) == 0
    assert (out / "index.html").is_file()
    assert "Wrote" in capsys.readouterr().out


def test_pages_load_nothing_remote(tmp_path):
    out = tmp_path / "lab"
    build_site(out, LabContext(), demos())
    pages = sorted(out.glob("*.html"))
    assert len(pages) == 2
    for page in pages:
        text = page.read_text(encoding="utf-8")
        assert not re.search(r"https?://|//cdn|@import|<link|<iframe|<script[^>]*\ssrc=", text)
        assert not re.search(r"fetch\(|XMLHttpRequest|WebSocket|EventSource|sendBeacon", text)
        assert "/*__LAB_" not in text and "__LAB_" not in text
        assert not re.search(r"<script[^>]*\ssrc=", text)  # inline data and inline code only


def test_pages_escape_script_terminators(tmp_path):
    out = tmp_path / "lab"
    hostile = Demo("h", "H", "s", lambda c: {"title": "</script><b>x</b>"}, "<p>h</p>")
    build_site(out, LabContext(), [hostile])
    assert (out / "h.html").read_text(encoding="utf-8").count("</script>") == 3


node = pytest.mark.skipif(shutil.which("node") is None, reason="node is needed to run page code")


def exported(tmp_path, state: dict) -> dict:
    build_site(tmp_path / "lab", LabContext(), demos())
    page = (tmp_path / "lab" / "index.html").read_text(encoding="utf-8")
    function = re.search(r"function buildVerdicts.*?\n}\n", page, re.S)[0]
    script = f"{function}\nconsole.log(JSON.stringify(buildVerdicts({json.dumps(state)})));"
    done = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


@node
def test_verdict_export_shape(tmp_path):
    state = {
        "demos": [{"name": "needy"}, {"name": "plain"}, {"name": "third"}],
        "verdicts": {
            "plain": {"verdict": "rework", "note": "  too busy  "},
            "needy": {"verdict": "maybe", "note": "not a verdict"},
        },
        "today": "2026-11-01",
    }
    assert exported(tmp_path, state) == {
        "exported_at": "2026-11-01",
        "demos": {"plain": {"verdict": "rework", "note": "too busy"}},
    }


@node
def test_verdicts_hold_no_track_data(tmp_path):
    state = {
        "demos": [{"name": "plain", "artist": NEEDLE, "tracks": [{"title": NEEDLE}]}],
        "verdicts": {"plain": {"verdict": "keep", "note": "", "artist": NEEDLE, "audio": "x"}},
        "today": "2026-11-01",
    }
    result = exported(tmp_path, state)
    assert NEEDLE not in json.dumps(result)
    assert set(result["demos"]["plain"]) == {"verdict", "note"}


@node
def test_home_works_without_local_storage(tmp_path):
    build_site(tmp_path / "lab", LabContext(), demos())
    page = (tmp_path / "lab" / "index.html").read_text(encoding="utf-8")
    code = re.search(r"<script>\n(.*?)</script>", page, re.S)[1]
    data = {
        "demos": [
            {
                "name": "plain",
                "title": "Plain",
                "summary": "s",
                "status": "ready",
                "href": "p.html",
            },
            {"name": "x", "title": "X", "summary": "s", "status": "unavailable", "reason": "r"},
        ]
    }
    # A browser whose storage throws, with just enough DOM for the page's code to run.
    harness = """
    const nodes = [];
    function make(tag) {
      return { tag, children: [], attrs: {}, listeners: {}, style: {}, set className(v) {},
        append(...c) { this.children.push(...c); }, setAttribute(k, v) { this.attrs[k] = v; },
        addEventListener(e, f) { this.listeners[e] = f; }, set textContent(v) { this.text = v; },
        get textContent() { return __DATA__; }, click() {} };
    }
    global.window = { get localStorage() { throw new Error("blocked"); } };
    global.document = { createElement: make, createTextNode: (t) => ({ text: t }),
      getElementById: (id) => id === "data" ? make("data") : make(id) };
    global.URL = { createObjectURL: () => "blob:x", revokeObjectURL() {} };
    global.Blob = function () {};
    """.replace("__DATA__", json.dumps(json.dumps(data)))
    script = harness + code + "\nconsole.log('ok');"
    done = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "ok"
