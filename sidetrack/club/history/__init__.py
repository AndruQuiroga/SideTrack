"""Local, evidence-based club history preparation; no network or database side effects."""

from .parser import preview
from .report import validate_plan, write_preview
from .sources import HistoryError, load_bundle, read_object


def check_plan(db, plan):
    """Reconcile against stored targets; keep DB dependencies out of offline preview."""
    from .check import check_plan as reconcile

    return reconcile(db, plan)


def apply_checked(db, checked, *, expected_digest, source_plan):
    """Apply the exact reconciled plan within the caller's transaction."""
    from .application import apply_checked as apply

    return apply(db, checked, expected_digest=expected_digest, source_plan=source_plan)


def verify_checked(db, checked):
    """Inspect stored batch targets without repair writes."""
    from .verification import verify_checked as verify

    return verify(db, checked)


__all__ = [
    "HistoryError",
    "load_bundle",
    "read_object",
    "preview",
    "validate_plan",
    "write_preview",
    "check_plan",
    "apply_checked",
    "verify_checked",
]
