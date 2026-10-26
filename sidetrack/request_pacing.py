"""Cross-process MusicBrainz request pacing using the existing Postgres database."""

from contextlib import contextmanager
from datetime import timedelta
from time import sleep

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from sidetrack.db import database_now, get_engine
from sidetrack.queue_models import RequestPacing


@contextmanager
def musicbrainz_request_slot():
    # Separate transaction: an import rollback must not undo request pacing.
    with Session(get_engine()) as db:
        now = database_now(db)
        db.execute(
            insert(RequestPacing)
            .values(name="musicbrainz", next_request_at=now)
            .on_conflict_do_nothing()
        )
        row = db.get(RequestPacing, "musicbrainz", with_for_update=True)
        now = database_now(db)
        delay = (row.next_request_at - now).total_seconds()
        if delay > 0:
            sleep(delay)
        try:
            yield
        finally:
            # Persist the next slot even if the external request fails. Hold the
            # row lock through the request so delayed callers cannot reorder starts.
            row.next_request_at = database_now(db) + timedelta(seconds=1.05)
            db.commit()


def wait_for_musicbrainz() -> None:
    with musicbrainz_request_slot():
        pass
