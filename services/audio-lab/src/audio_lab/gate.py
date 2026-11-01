"""Evaluation gate for user-facing analysis claims (spec: analysis/evaluation-gates).

A record is a JSON object written outside the repository. ``check_record`` says whether it is
complete, ``derive_status`` combines that with the owner's decision, and ``summarize`` writes the
only part that may be committed: aggregate figures from an allow-list, never a title or a path.
This module acquires no audio and starts no subprocess or network call.
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

from .seeds import OutputInRepo, ensure_outside_repo, repo_root

SCHEMA_VERSION = 1
TASKS = ("neighbours", "text_label", "mood", "timing", "eras", "other")
SOURCES = ("preview", "full", "mixed")
GROUPINGS = ("artist", "recording", "none")
DECISIONS = ("approve", "reject", "correct")
STATUS_VALUES = ("approved", "gate_pending", "incomplete", "rejected")
CHALLENGE_CATEGORIES = ("obscure", "electronic", "altered")
SAMPLING_UNITS = ("track", "recording", "artist")
# The summary directory is the one place inside the working tree that `gate summarize` may write.
SUMMARY_DIR = ("docs", "evaluations", "summaries")

# Predicted valence and arousal this correlated may not be distinguishable (notes, section 3).
AXIS_WARNING_CORRELATION = 0.8
UNGROUPED_CAVEAT = "not artist-grouped: scores may be optimistic"
CONFIDENCE_WORDS = re.compile(r"\b(confidence|confident|probability|probable|certainty)\b", re.I)
SECTION_LABELS = (
    "intro",
    "verse",
    "chorus",
    "bridge",
    "outro",
    "drop",
    "breakdown",
    "buildup",
    "solo",
)
LEAKAGE_KEYS = ("audio_sha256", "recording_id", "upload_group")
COVERAGE_COUNTS = (
    "missing_audio",
    "ambiguous_links",
    "short_files",
    "model_failures",
    "unknown_or_abstained",
    "rater_disagreement",
)
# Counts that remove an item from the evaluation. The rest are reported but not excluded.
EXCLUDING_COUNTS = ("missing_audio", "ambiguous_links", "short_files", "model_failures")
HEADER_TEXT = (
    "record_id",
    "claim",
    "claim_wording",
    "model",
    "checkpoint_revision",
    "probe_revision",
    "pipeline",
    "vocabulary",
    "vocabulary_version",
    "preprocessing",
    "evaluated_on",
)
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@+/-]{0,95}$")
AUDIO_SUFFIX = re.compile(r"\.(mp3|flac|wav|ogg|opus|m4a|aac|aiff?)$", re.I)

# Numeric task figures that may enter a summary, as dotted paths into the task section.
SUMMARY_METRICS: dict[str, tuple[str, ...]] = {
    "neighbours": (
        "pairwise_judgments.count",
        "ranking.value",
        "random_control.precision",
        "recent_or_frequent_baseline.precision",
    ),
    "text_label": (
        "hard_negatives.count",
        "abstention.abstained",
        "raw_vs_relative.raw_cosine.accuracy",
        "raw_vs_relative.library_relative.accuracy",
    ),
    "mood": tuple(
        f"axes.{axis}.{name}"
        for axis in ("valence", "arousal")
        for name in ("r2", "mean_only_baseline_r2", "rank_correlation", "calibration_coverage")
    ),
    "timing": (
        "tolerance_s",
        "boundary_accuracy",
        "label_accuracy",
        "half_double_tempo_agreement",
    ),
    "eras": ("periods", "missing_periods", "interpolated_periods", "seed_stability"),
    "other": (),
}


class GateError(ValueError):
    """A record or decision that cannot be processed at all."""


def _get(data: Any, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(data, dict) or part not in data:
            return None
        data = data[part]
    return data


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str | list | dict) and len(value) == 0)


def _moment(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class _Findings:
    def __init__(self) -> None:
        self.missing: list[str] = []
        self.messages: list[str] = []
        self.flags: list[str] = []
        self.warnings: list[str] = []

    def need(self, ok: bool, field: str, message: str | None = None) -> bool:
        if not ok:
            if field not in self.missing:
                self.missing.append(field)
            self.messages.append(f"{field}: {message or 'missing or invalid'}")
        return ok


def _check_header(record: dict, f: _Findings) -> None:
    for field in HEADER_TEXT:
        f.need(isinstance(record.get(field), str) and bool(record[field].strip()), field)
    f.need(record.get("task") in TASKS, "task", f"must be one of {', '.join(TASKS)}")
    f.need(record.get("source") in SOURCES, "source", f"must be one of {', '.join(SOURCES)}")
    duration = record.get("analyzed_duration_s")
    f.need(_is_number(duration) and duration > 0, "analyzed_duration_s")
    f.need(not _blank(record.get("time_range")), "time_range")
    population = record.get("population")
    f.need(isinstance(population, dict) and _is_count(population.get("items")), "population")
    f.need(
        isinstance(record.get("datasets"), list)
        and all(isinstance(d, str) for d in record["datasets"]),
        "datasets",
        "a list of dataset ids (empty when none are cited)",
    )
    f.need(isinstance(record.get("raters"), int) and record["raters"] >= 1, "raters")
    if "evaluated_on" in record:
        f.need(_moment(record["evaluated_on"]) is not None, "evaluated_on", "not an ISO date")


def _check_challenge(record: dict, f: _Findings) -> list[str]:
    challenge = record.get("challenge")
    ok = isinstance(challenge, dict) and challenge.get("held_out") is True
    f.need(ok, "challenge", "needs held_out: true and a count for each category")
    not_covered = []
    for category in CHALLENGE_CATEGORIES:
        count = challenge.get(category) if isinstance(challenge, dict) else None
        if not _is_count(count) or count == 0:
            not_covered.append(category)
    return not_covered


def _check_grouping(record: dict, f: _Findings) -> str | None:
    """Return the caveat to show next to fitted metrics, if any."""

    fits = record.get("fits")
    if not f.need(isinstance(fits, bool), "fits", "state whether anything was fitted"):
        return None
    if not fits:
        return None
    grouping = record.get("grouping")
    mode = grouping.get("mode") if isinstance(grouping, dict) else None
    if not f.need(mode in GROUPINGS, "grouping", f"mode must be one of {', '.join(GROUPINGS)}"):
        return None
    if mode == "none":
        reason = grouping.get("reason")
        f.need(
            isinstance(reason, str) and bool(reason.strip()), "grouping", "mode none needs a reason"
        )
    _check_leakage(record, f)
    return None if mode == "artist" else UNGROUPED_CAVEAT


def _check_leakage(record: dict, f: _Findings) -> None:
    items = record.get("items")
    if not f.need(isinstance(items, list) and bool(items), "items", "fitted records list items"):
        return
    folds: dict[tuple[str, str], set] = defaultdict(set)
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in LEAKAGE_KEYS:
            if item.get(key):
                folds[(key, str(item[key]))].add(item.get("fold"))
    accepted = {
        str(a.get("key"))
        for a in record.get("accepted_leakage", [])
        if isinstance(a, dict) and isinstance(a.get("reason"), str) and a["reason"].strip()
    }
    for (key, value), seen in sorted(folds.items()):
        if len(seen) > 1 and value not in accepted:
            f.need(False, "duplicate_items", f"{key} {value} appears in more than one fold")


def _check_coverage(record: dict, f: _Findings) -> dict | None:
    coverage = record.get("coverage")
    if not f.need(isinstance(coverage, dict), "coverage"):
        return None
    names = ("total_items", "evaluated", *COVERAGE_COUNTS)
    bad = [n for n in names if not _is_count(coverage.get(n))]
    if not f.need(not bad, "coverage", f"counts missing or invalid: {', '.join(bad)}"):
        return None
    other = coverage.get("excluded_other", [])
    valid_other = isinstance(other, list) and all(
        isinstance(e, dict) and _is_count(e.get("count")) and e.get("reason") for e in other
    )
    if not f.need(valid_other, "coverage", "excluded_other needs a reason and count each"):
        return None
    excluded = sum(coverage[n] for n in EXCLUDING_COUNTS) + sum(e["count"] for e in other)
    total = coverage["total_items"]
    f.need(
        total > 0 and coverage["evaluated"] + excluded == total,
        "coverage_counts",
        f"evaluated {coverage['evaluated']} + excluded {excluded} must equal total {total}",
    )
    population = record.get("population")
    if isinstance(population, dict) and _is_count(population.get("items")):
        f.need(
            population["items"] == total,
            "coverage_counts",
            "population.items must equal coverage.total_items",
        )
    if total <= 0:
        return None
    fraction = Fraction(excluded, total)
    return {
        **{n: coverage[n] for n in names},
        "excluded": excluded,
        "excluded_fraction": f"{fraction.numerator}/{fraction.denominator}",
        "excluded_fraction_value": round(float(fraction), 4),
    }


def _check_robustness(record: dict, f: _Findings) -> None:
    robustness = record.get("robustness")
    if not f.need(isinstance(robustness, dict), "robustness"):
        return
    change = robustness.get("material_change")
    f.need(_is_number(change) and change > 0, "material_change", "declare it before scoring")
    f.need(
        robustness.get("sampling_unit") in SAMPLING_UNITS,
        "sampling_unit",
        f"must be one of {', '.join(SAMPLING_UNITS)}, not individual plays",
    )
    f.need(
        isinstance(robustness.get("uncertainty"), dict) and bool(robustness["uncertainty"]),
        "uncertainty",
        "report an interval for the sampling unit",
    )
    comparison = robustness.get("preview_vs_full")
    valid = isinstance(comparison, dict) and (
        _is_number(comparison.get("delta")) or bool(comparison.get("not_applicable"))
    )
    f.need(valid, "preview_vs_full", "a delta, or not_applicable with a reason")
    if valid and _is_number(comparison.get("delta")) and _is_number(change):
        if abs(comparison["delta"]) > change:
            f.flags.append("preview_robustness_failed")


def _check_times(record: dict, f: _Findings) -> None:
    declared, scored = _moment(record.get("declared_at")), _moment(record.get("scored_at"))
    f.need(declared is not None, "declared_at", "thresholds must be declared before scoring")
    f.need(scored is not None, "scored_at")
    if declared and scored:
        f.need(declared < scored, "declared_at", "thresholds were declared after scoring")


def _check_neighbours(section: dict, record: dict, f: _Findings) -> dict:
    judged = section.get("pairwise_judgments")
    f.need(
        isinstance(judged, dict)
        and judged.get("blind") is True
        and _is_count(judged.get("count"))
        and judged["count"] > 0,
        "pairwise_judgments",
        "blind pairwise judgments with a count",
    )
    f.need(_is_number(_get(section, "ranking.value")), "ranking", "a precision or ranking measure")
    f.need(_is_number(_get(section, "random_control.precision")), "random_control")
    f.need(
        _is_number(_get(section, "recent_or_frequent_baseline.precision")),
        "recent_or_frequent_baseline",
    )
    if CONFIDENCE_WORDS.search(record.get("claim_wording") or ""):
        f.need(False, "uncalibrated_confidence", "similarity is not a confidence")
    judgments = section.get("judgments")
    if not f.need(isinstance(judgments, list) and bool(judgments), "judgments"):
        return {}
    same = similar = not_similar = 0
    for j in judgments:
        if not isinstance(j, dict):
            continue
        if (
            j.get("verdict") == "same_recording"
            or j.get("is_seed_preview")
            or j.get("is_version_of_seed")
        ):
            same += 1
        elif j.get("verdict") == "similar":
            similar += 1
        else:
            not_similar += 1
    judged_similar = similar + not_similar
    return {
        "same_recording": same,
        "judged_for_similarity": judged_similar,
        "similar_precision": round(similar / judged_similar, 4) if judged_similar else None,
    }


def _check_text_label(section: dict, record: dict, f: _Findings) -> dict:
    variants = section.get("prompt_variants")
    ok = (
        isinstance(variants, dict)
        and bool(variants)
        and all(isinstance(v, list) and len(set(v)) >= 2 for v in variants.values())
    )
    f.need(ok, "prompt_variants", "several distinct prompts for every term")
    f.need(
        _is_count(_get(section, "hard_negatives.count")) and section["hard_negatives"]["count"] > 0,
        "hard_negatives",
    )
    f.need(_get(section, "abstention.supported") is True, "abstention")
    f.need(
        _is_number(_get(section, "raw_vs_relative.raw_cosine.accuracy"))
        and _is_number(_get(section, "raw_vs_relative.library_relative.accuracy")),
        "raw_vs_relative",
        "compare raw cosine with library-relative ranking",
    )
    if CONFIDENCE_WORDS.search(record.get("claim_wording") or ""):
        f.need(False, "uncalibrated_confidence", "a cosine or z-score is not a probability")
    return {"terms": len(variants) if isinstance(variants, dict) else 0}


def _check_mood(section: dict, f: _Findings) -> dict:
    axes = section.get("axes")
    for axis in ("valence", "arousal"):
        body = axes.get(axis) if isinstance(axes, dict) else None
        if not f.need(isinstance(body, dict), axis, "evaluate both axes"):
            continue
        for name in ("r2", "mean_only_baseline_r2", "rank_correlation", "calibration_coverage"):
            f.need(_is_number(body.get(name)), f"{axis}.{name}")
    predicted, human = (
        _get(section, f"axis_correlation.{k}") for k in ("predicted_library", "human")
    )
    f.need(
        _is_number(predicted) and _is_number(human),
        "axis_correlation",
        "predicted (target library) and human correlations",
    )
    if _is_number(predicted) and abs(predicted) >= AXIS_WARNING_CORRELATION:
        return {
            "axis_warning": (
                f"predicted valence and arousal correlate at {predicted:.2f} "
                f"(human ratings {human if _is_number(human) else 'unreported'}): "
                "the axes may not be distinguished"
            )
        }
    return {}


def _check_timing(section: dict, record: dict, f: _Findings) -> dict:
    targets = section.get("targets")
    valid_targets = isinstance(targets, list) and bool(targets)
    f.need(valid_targets, "targets", "beats, downbeats, tempo and/or sections")
    targets = targets if valid_targets else []
    tolerance = section.get("tolerance_s")
    f.need(_is_number(tolerance) and tolerance > 0, "tolerance_s", "declare it before scoring")
    f.need(_is_number(section.get("boundary_accuracy")), "boundary_accuracy")
    if "sections" in targets:
        f.need(_is_number(section.get("label_accuracy")), "label_accuracy")
    if "tempo" in targets:
        f.need(
            _is_number(section.get("half_double_tempo_agreement")), "half_double_tempo_agreement"
        )
    reference = section.get("reference_classes")
    f.need(isinstance(reference, list), "reference_classes")
    reference = {str(c).lower() for c in reference} if isinstance(reference, list) else set()
    wording_words = set(re.findall(r"[a-z]+", (record.get("claim_wording") or "").lower()))
    claimed = {str(c).lower() for c in section.get("claimed_labels", [])}
    claimed |= wording_words & set(SECTION_LABELS)
    unsupported = sorted(claimed - reference)
    if unsupported:
        f.need(
            False, "unsupported_label", f"no reference annotations for: {', '.join(unsupported)}"
        )
    return {}


def _check_eras(section: dict, f: _Findings) -> dict:
    f.need(_is_count(section.get("periods")) and section["periods"] > 0, "periods")
    f.need(_is_count(section.get("missing_periods")), "missing_periods")
    f.need(
        section.get("interpolated_periods") == 0,
        "interpolated_periods",
        "missing periods stay missing",
    )
    f.need(_is_number(section.get("seed_stability")), "seed_stability")
    return {}


def _check_other(section: dict, f: _Findings) -> dict:
    plan = section.get("metric_plan")
    f.need(isinstance(plan, str) and bool(plan.strip()), "metric_plan")
    return {}


def check_record(record: dict) -> dict:
    """Completeness of a record: status ``complete`` or ``incomplete`` plus every finding."""

    if not isinstance(record, dict):
        raise GateError("A record is a JSON object.")
    f = _Findings()
    _check_header(record, f)
    not_covered = _check_challenge(record, f)
    caveat = _check_grouping(record, f)
    coverage = _check_coverage(record, f)
    _check_robustness(record, f)
    _check_times(record, f)
    derived: dict = {}
    task = record.get("task")
    section = record.get(task) if task in TASKS else None
    if task in TASKS and f.need(isinstance(section, dict), str(task), "task section missing"):
        if task == "neighbours":
            derived = _check_neighbours(section, record, f)
        elif task == "text_label":
            derived = _check_text_label(section, record, f)
        elif task == "mood":
            derived = _check_mood(section, f)
        elif task == "timing":
            derived = _check_timing(section, record, f)
        elif task == "eras":
            derived = _check_eras(section, f)
        else:
            derived = _check_other(section, f)
    if derived.get("axis_warning"):
        f.warnings.append(derived["axis_warning"])
    if caveat:
        f.warnings.append(caveat)
    if record.get("raters") == 1:
        f.warnings.append("one rater: approves the claim for the owner's library only")
    return {
        "status": "incomplete" if f.missing else "complete",
        "missing": f.missing,
        "messages": f.messages,
        "not_covered": not_covered,
        "flags": f.flags,
        "warnings": f.warnings,
        "caveat": caveat,
        "coverage": coverage,
        "derived": derived,
    }


def derive_status(record: dict, check: dict | None = None) -> str:
    """Gate status: ``approved``, ``gate_pending``, ``incomplete`` or ``rejected``."""

    check = check or check_record(record)
    decision = (record.get("decision") or {}).get("decision")
    if decision == "reject":
        return "rejected"
    if check["status"] != "complete":
        return "incomplete"
    return "approved" if decision == "approve" else "gate_pending"


def import_decision(record: dict, decision: dict) -> dict:
    """Return a copy of ``record`` carrying the owner's decision; earlier ones are kept."""

    kind = decision.get("decision")
    if kind not in DECISIONS:
        raise GateError(f"decision must be one of {', '.join(DECISIONS)}")
    when = decision.get("decided_at")
    if not isinstance(when, str) or _moment(when) is None:
        raise GateError("decided_at must be an ISO date")
    reviewed = decision.get("reviewed_examples")
    if not _is_count(reviewed) or reviewed == 0:
        raise GateError("reviewed_examples must be the number of examples the owner reviewed")
    notes = decision.get("notes", "")
    corrections = decision.get("corrections", [])
    if kind == "reject" and not str(notes).strip():
        raise GateError("a rejection keeps a note")
    if kind == "correct" and not corrections:
        raise GateError("a correction lists at least one corrected example")
    kept = {
        "decision": kind,
        "decided_at": when,
        "notes": str(notes),
        "corrections": corrections,
        "reviewed_examples": reviewed,
    }
    updated = dict(record)
    if isinstance(record.get("decision"), dict):
        updated["decision_history"] = [*record.get("decision_history", []), record["decision"]]
    updated["decision"] = kept
    return updated


def _safe(value: Any, field: str) -> str | None:
    if value is None or value == "":
        return None
    text = str(value)
    if not SAFE_TOKEN.match(text) or AUDIO_SUFFIX.search(text) or ".." in text:
        raise GateError(f"{field} {text!r} cannot go in a committed summary")
    return text


def summarize(record: dict) -> dict:
    """Aggregate figures only: an allow-list of fields, with no titles, paths or per-item values."""

    check = check_record(record)
    task = record.get("task")
    section = record.get(task) if task in TASKS else None
    caveat = check["caveat"]
    fits = record.get("fits") is True
    metrics = []
    if isinstance(section, dict):
        for path in SUMMARY_METRICS[task]:
            value = _get(section, path)
            if _is_number(value):
                metrics.append(
                    {
                        "name": path,
                        "value": value,
                        "fitted": fits,
                        "caveat": caveat if fits else None,
                    }
                )
    for name, value in check["derived"].items():
        if _is_number(value):
            metrics.append({"name": name, "value": value, "fitted": False, "caveat": None})
    challenge = record.get("challenge") if isinstance(record.get("challenge"), dict) else {}
    decision = record.get("decision") if isinstance(record.get("decision"), dict) else {}
    summary = {
        "schema_version": SCHEMA_VERSION,
        "record_id": _safe(record.get("record_id", ""), "record_id"),
        "claim": _safe(record.get("claim", ""), "claim"),
        "task": task if task in TASKS else None,
        "status": derive_status(record, check),
        "revisions": {
            name: _safe(record.get(name, ""), name)
            for name in (
                "model",
                "checkpoint_revision",
                "probe_revision",
                "pipeline",
                "vocabulary_version",
            )
        },
        "source": record.get("source") if record.get("source") in SOURCES else None,
        "analyzed_duration_s": record.get("analyzed_duration_s")
        if _is_number(record.get("analyzed_duration_s"))
        else None,
        "datasets": [_safe(d, "datasets") for d in record.get("datasets", []) if d],
        "raters": record.get("raters") if _is_count(record.get("raters")) else None,
        "scope": "owner library only" if record.get("raters") == 1 else None,
        "challenge": {
            c: challenge.get(c) if _is_count(challenge.get(c)) else 0 for c in CHALLENGE_CATEGORIES
        },
        "not_covered": check["not_covered"],
        "grouping": (record.get("grouping") or {}).get("mode") if fits else None,
        "coverage": check["coverage"],
        "metrics": metrics,
        "flags": check["flags"],
        "warnings": check["warnings"],
        "missing": check["missing"],
        "decision": {
            "decision": decision.get("decision"),
            "decided_at": decision.get("decided_at"),
            "reviewed_examples": decision.get("reviewed_examples"),
            "corrections": len(decision.get("corrections", [])),
        }
        if decision
        else None,
    }
    return summary


def ensure_output_allowed(out: Path, *, summary: bool = False) -> None:
    """Refuse a path inside the working tree; a summary may go to docs/evaluations/summaries."""

    try:
        ensure_outside_repo(out)
    except OutputInRepo:
        root = repo_root(Path(__file__).resolve().parent)
        if summary and root is not None:
            allowed = root.joinpath(*SUMMARY_DIR)
            target = out.resolve()
            if allowed in target.parents:
                return
        raise


def prepare_annotation_only(metadata: Path, audio_dir: Path | None, id_column: str = "id") -> dict:
    """Report which dataset items have local audio. It prepares nothing and fetches nothing.

    For datasets whose audio exists only as YouTube references (MusicCaps, Harmonix): an item
    counts as ``no_local_audio`` unless the owner already holds a file named after its id.
    """

    with metadata.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if rows and id_column not in rows[0]:
        raise GateError(f"{metadata} has no {id_column!r} column")
    held: set[str] = set()
    if audio_dir is not None and audio_dir.is_dir():
        held = {p.stem for p in audio_dir.iterdir() if p.is_file()}
    with_audio = sum(1 for r in rows if r[id_column] in held)
    return {
        "items": len(rows),
        "local_audio": with_audio,
        "no_local_audio": len(rows) - with_audio,
        "audio_prepared": 0,
        "downloads_started": 0,
    }


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GateError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise GateError(f"{path} is not a JSON object")
    return data
