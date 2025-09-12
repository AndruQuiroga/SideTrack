import logging


def setup_logging(level: int = logging.INFO) -> None:
    """Configure standard logging with a simple, readable format."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
