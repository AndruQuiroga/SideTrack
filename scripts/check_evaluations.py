"""Check the analysis evaluation registers against each other and against docs/status.yaml.

Usage:
    python scripts/check_evaluations.py          # exit 1 on any error
    python scripts/check_evaluations.py --links  # also check relative links in the evaluation docs

Spec: analysis/evaluation-gates. Reads docs/evaluations/register.yaml (one entry per claim) and
datasets.yaml (one entry per evaluation dataset). It never reads a record, audio or an
annotation file: only the committed registers and aggregate summaries.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
EVALUATIONS = Path("docs") / "evaluations"
CLAIM_STATUSES = ("approved", "gate_pending", "incomplete", "rejected", "stale")
AUDIO_STATUSES = (
    "recorded",
    "owner_accepted",
    "rights_unconfirmed",
    "annotation_only",
    "not_for_use",
)
ANNOTATION_STATUSES = ("recorded", "owner_accepted", "rights_unconfirmed", "not_for_use")
# Statuses an approved claim may cite. `owner_accepted` means the terms are still unconfirmed.
USABLE_STATUSES = ("recorded", "owner_accepted")
ACCEPTANCE_FIELDS = ("date", "by", "scope")
USES = ("audio", "annotations")
ACQUISITIONS = ("owner_manual", "none")
REVISION_FIELDS = (
    "model",
    "checkpoint_revision",
    "probe_revision",
    "pipeline",
    "vocabulary_version",
)
REVIEW_MAX_AGE_DAYS = 365
# Docs that link to docs/evaluations/, checked by --links together with the evaluation docs.
LINKING_DOCS = (
    Path("docs") / "AUDIO-BENCHMARK.md",
    Path("docs") / "research" / "MUSIC-ANALYSIS.md",
)
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _load(path: Path, errors: list[str]) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        errors.append(f"{path}: {exc.strerror or exc}")
    except yaml.YAMLError as exc:
        errors.append(f"{path}: invalid YAML ({exc})")
    return None


def _as_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def check_datasets(data: Any, today: date) -> tuple[dict[str, dict], list[str], list[str]]:
    """Validate datasets.yaml. Returns the datasets by id, errors and warnings."""

    errors: list[str] = []
    warnings: list[str] = []
    found: dict[str, dict] = {}
    entries = data.get("datasets") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        return found, ["datasets.yaml: needs a non-empty 'datasets' list"], warnings
    for entry in entries:
        name = entry.get("id", "<no id>") if isinstance(entry, dict) else "<entry>"
        if not isinstance(entry, dict) or not entry.get("id"):
            errors.append(f"datasets.yaml: {name}: every dataset needs an id")
            continue
        if name in found:
            errors.append(f"datasets.yaml: {name}: duplicate id")
        found[name] = entry
        for field in ("name", "url", "use", "audio_terms", "annotation_terms", "storage"):
            if not entry.get(field):
                errors.append(f"datasets.yaml: {name}: missing {field}")
        if not isinstance(entry.get("gaps"), list):
            errors.append(f"datasets.yaml: {name}: gaps must be a list (empty when none known)")
        status = entry.get("status") if isinstance(entry.get("status"), dict) else {}
        if status.get("audio") not in AUDIO_STATUSES:
            errors.append(f"datasets.yaml: {name}: status.audio must be one of {AUDIO_STATUSES}")
        if status.get("annotations") not in ANNOTATION_STATUSES:
            errors.append(
                f"datasets.yaml: {name}: status.annotations must be one of {ANNOTATION_STATUSES}"
            )
        if "owner_accepted" in status.values():
            acceptance = entry.get("acceptance")
            acceptance = acceptance if isinstance(acceptance, dict) else {}
            for field in ACCEPTANCE_FIELDS:
                if not acceptance.get(field):
                    errors.append(f"datasets.yaml: {name}: acceptance needs {field}")
        if entry.get("acquisition") not in ACQUISITIONS:
            errors.append(
                f"datasets.yaml: {name}: acquisition must be one of {ACQUISITIONS}, "
                "never automated or scheduled"
            )
        if "outside" not in str(entry.get("storage", "")).lower():
            errors.append(f"datasets.yaml: {name}: storage must be outside the repo")
        if (
            entry.get("audio_source") == "youtube_reference"
            and status.get("audio") != "annotation_only"
            and not entry.get("owner_holds_audio")
        ):
            errors.append(
                f"datasets.yaml: {name}: audio exists only as YouTube references, so "
                "status.audio must be annotation_only unless the owner holds the audio"
            )
        if entry.get("recheck") is not True:
            errors.append(f"datasets.yaml: {name}: recheck must stay true until terms are verified")
        reviewed = _as_date(entry.get("reviewed"))
        if reviewed is None:
            errors.append(f"datasets.yaml: {name}: reviewed must be a date")
        elif (today - reviewed).days > REVIEW_MAX_AGE_DAYS:
            warnings.append(
                f"datasets.yaml: {name}: last reviewed {reviewed}, "
                f"over {REVIEW_MAX_AGE_DAYS} days ago"
            )
    return found, errors, warnings


def _load_summary(root: Path, claim: dict, errors: list[str]) -> dict | None:
    name = claim["claim"]
    path = claim.get("summary")
    if not path:
        errors.append(f"{name}: approved without a summary file")
        return None
    full = root / path
    if not full.is_file():
        errors.append(f"{name}: summary {path} does not exist")
        return None
    try:
        summary = json.loads(full.read_text(encoding="utf-8"))
    except ValueError as exc:
        errors.append(f"{name}: summary {path} is not valid JSON ({exc})")
        return None
    return summary if isinstance(summary, dict) else None


def _check_approved(root: Path, claim: dict, datasets: dict[str, dict], errors: list[str]) -> None:
    name = claim["claim"]
    summary = _load_summary(root, claim, errors)
    declared = claim.get("feature_revisions") or {}
    if summary is not None:
        if summary.get("claim") != name:
            errors.append(f"{name}: summary is for claim {summary.get('claim')!r}")
        if summary.get("status") != "approved" or (
            (summary.get("decision") or {}).get("decision") != "approve"
        ):
            errors.append(f"{name}: approved needs a complete summary with an owner approve")
        evaluated = summary.get("revisions") or {}
        differing = [
            f"{field} {evaluated.get(field)!r} evaluated vs {declared.get(field)!r} declared"
            for field in REVISION_FIELDS
            if evaluated.get(field) != declared.get(field)
        ]
        if differing:
            errors.append(f"{name}: stale, not approved ({'; '.join(differing)})")
    for ref in claim.get("datasets") or []:
        _check_dataset_use(name, ref, datasets, errors)


def _check_dataset_use(name: str, ref: Any, datasets: dict[str, dict], errors: list[str]) -> None:
    ref = ref if isinstance(ref, dict) else {"id": ref}
    dataset_id, use = ref.get("id"), ref.get("use")
    if use not in USES:
        errors.append(f"{name}: dataset {dataset_id!r} needs use: audio or annotations")
        return
    entry = datasets.get(dataset_id)
    if entry is None:
        return
    status = (entry.get("status") or {}).get(use)
    if status not in USABLE_STATUSES:
        errors.append(
            f"{name}: cites {entry.get('name', dataset_id)} {use}, "
            f"whose rights status is {status}; it cannot be approved"
        )


def check_claims(
    root: Path, data: Any, datasets: dict[str, dict], status_data: Any
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    entries = data.get("claims") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return ["register.yaml: needs a 'claims' list"], warnings
    works = _works_capabilities(status_data)
    known = _capabilities(status_data)
    seen: set[str] = set()
    for claim in entries:
        if not isinstance(claim, dict) or not claim.get("claim"):
            errors.append("register.yaml: every entry needs a claim id")
            continue
        name = claim["claim"]
        if name in seen:
            errors.append(f"{name}: duplicate claim")
        seen.add(name)
        status = claim.get("status")
        if status not in CLAIM_STATUSES:
            errors.append(f"{name}: status must be one of {CLAIM_STATUSES}, not {status!r}")
            continue
        if not claim.get("title"):
            errors.append(f"{name}: missing title")
        revisions = claim.get("feature_revisions")
        if not isinstance(revisions, dict) or any(not revisions.get(f) for f in REVISION_FIELDS):
            errors.append(f"{name}: feature_revisions needs {', '.join(REVISION_FIELDS)}")
        unregistered = sorted(
            {
                str(ref.get("id") if isinstance(ref, dict) else ref)
                for ref in claim.get("datasets") or []
            }
            - set(datasets)
        )
        if unregistered:
            if status not in ("incomplete", "rejected"):
                errors.append(
                    f"{name}: cites {', '.join(unregistered)}, which is not in datasets.yaml; "
                    f"the entry is incomplete, not {status}"
                )
        if status == "approved":
            _check_approved(root, claim, datasets, errors)
        for capability in claim.get("capabilities") or []:
            if capability not in known:
                errors.append(f"{name}: capability {capability!r} is not in docs/status.yaml")
            elif capability in works and status != "approved":
                errors.append(
                    f"{name}: status is {status}, but docs/status.yaml marks "
                    f"{capability!r} works"
                )
    return errors, warnings


def _capabilities(status_data: Any) -> dict[str, str]:
    found: dict[str, str] = {}
    for group in (status_data or {}).get("groups", []) or []:
        for item in group.get("items", []) or []:
            found[item.get("capability")] = item.get("status")
    return found


def _works_capabilities(status_data: Any) -> set[str]:
    return {name for name, status in _capabilities(status_data).items() if status == "works"}


def check(root: Path = ROOT, today: date | None = None) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for the evaluation registers under ``root``."""

    today = today or date.today()
    errors: list[str] = []
    directory = root / EVALUATIONS
    datasets_data = _load(directory / "datasets.yaml", errors)
    register_data = _load(directory / "register.yaml", errors)
    status_data = _load(root / "docs" / "status.yaml", errors)
    if errors:
        return errors, []
    datasets, dataset_errors, warnings = check_datasets(datasets_data, today)
    claim_errors, claim_warnings = check_claims(root, register_data, datasets, status_data)
    return [*dataset_errors, *claim_errors], [*warnings, *claim_warnings]


def check_links(root: Path = ROOT) -> list[str]:
    """Relative markdown links in the evaluation docs and the docs that point at them."""

    errors: list[str] = []
    files = sorted((root / EVALUATIONS).glob("*.md")) + [root / p for p in LINKING_DOCS]
    for file in files:
        if not file.is_file():
            errors.append(f"{file.relative_to(root)}: missing")
            continue
        for target in LINK.findall(file.read_text(encoding="utf-8")):
            if re.match(r"^[a-z][a-z0-9+.-]*:|^#", target):
                continue
            if not (file.parent / target.split("#", 1)[0]).exists():
                errors.append(f"{file.relative_to(root)}: broken link {target}")
    for doc in LINKING_DOCS:
        path = root / doc
        if path.is_file() and "evaluations/" not in path.read_text(encoding="utf-8"):
            errors.append(f"{doc}: does not link to docs/evaluations/")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--links", action="store_true", help="also check relative doc links")
    args = parser.parse_args(argv)
    errors, warnings = check()
    if args.links:
        errors += check_links()
    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    print("Evaluation registers are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
