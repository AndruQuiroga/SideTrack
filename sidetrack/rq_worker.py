"""Legacy entrypoint forwarding to the Postgres worker, without importing RQ."""

from sidetrack.worker import main

__all__ = ["main"]

if __name__ == "__main__":
    main()
