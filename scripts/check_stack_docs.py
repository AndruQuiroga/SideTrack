"""Fail if deploy/README.md doesn't mention every secret and variable in deploy/stack.yml.

Usage: python scripts/check_stack_docs.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STACK = ROOT / "deploy" / "stack.yml"
README = ROOT / "deploy" / "README.md"

# Variables Swarm or Docker supply, not the operator.
IGNORED_VARS: set[str] = set()


def stack_requirements(stack_text: str) -> tuple[set[str], set[str]]:
    stack = yaml.safe_load(stack_text)
    secrets = set((stack.get("secrets") or {}).keys())
    variables = set(re.findall(r"\$\{([A-Z0-9_]+)", stack_text)) - IGNORED_VARS
    return secrets, variables


def main() -> int:
    secrets, variables = stack_requirements(STACK.read_text(encoding="utf-8"))
    readme = README.read_text(encoding="utf-8")
    missing = sorted(name for name in secrets | variables if f"`{name}`" not in readme)
    if missing:
        print("deploy/README.md is missing:", ", ".join(missing))
        return 1
    print(f"deploy/README.md documents {len(secrets)} secrets and {len(variables)} variables.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
