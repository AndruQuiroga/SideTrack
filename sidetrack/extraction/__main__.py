"""Entry point for ``python -m sidetrack.extraction``."""

from __future__ import annotations

import warnings

from .cli import app


def main() -> None:
    warnings.warn(
        "`python -m sidetrack.extraction` is deprecated; use "
        "`python -m sidetrack extract ...` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    app()


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
