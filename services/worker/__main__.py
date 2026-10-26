"""Retired legacy sync worker (ADR 0002 and ADR 0003)."""


def main():
    raise SystemExit(
        "services.worker is retired. Apply Alembic migrations and run "
        "python -m sidetrack.worker instead. Spotify sync and audio features are unavailable."
    )


if __name__ == "__main__":
    main()
