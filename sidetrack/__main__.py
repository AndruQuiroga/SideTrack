"""Entry point for ``python -m sidetrack``."""

from __future__ import annotations

from .cli import app


def main() -> None:
    """Execute the Typer application."""

    app()


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
