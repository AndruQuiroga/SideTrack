"""The supported runtime has only the Postgres stateful service."""

import ast
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_no_retired_queue_imports_or_dependencies():
    prohibited = {"redis", "rq", "apscheduler", "fastapi_limiter"}
    for package in [ROOT / "sidetrack", ROOT / "services"]:
        for source in package.rglob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                modules = (
                    [a.name for a in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                    if isinstance(node, ast.ImportFrom)
                    else []
                )
                assert not prohibited.intersection(m.split(".")[0] for m in modules), source
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dependencies = project["project"]["dependencies"] + [
        dep for group in project["project"]["optional-dependencies"].values() for dep in group
    ]
    assert not any(dep.split("=")[0].split("[")[0] in prohibited for dep in dependencies)


def test_stack_services_and_worker_commands():
    for path in [ROOT / "compose.yml", ROOT / "deploy/stack.yml"]:
        services = yaml.safe_load(path.read_text())["services"]
        assert "redis" not in services
        assert "rq-worker" not in services
        assert services["worker"]["command"] == ["python", "-m", "sidetrack.worker"]
