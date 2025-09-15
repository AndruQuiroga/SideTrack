"""Entry point for ``python -m sidetrack.extraction``."""

from .cli import app


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
