from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager, suppress

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from sidetrack.api.db import SessionLocal


@contextmanager
def session_scope(*, commit: bool = False) -> Iterator[Session]:
    """Yield a synchronous :class:`Session` and ensure it is closed.

    Parameters
    ----------
    commit:
        When ``True`` the session is committed when the context exits
        successfully. Any exception triggers a rollback before the
        exception is re-raised.
    """

    session = SessionLocal(async_session=False)
    try:
        yield session
        if commit:
            session.commit()
    except BaseException:
        with suppress(Exception):
            session.rollback()
        raise
    finally:
        with suppress(Exception):
            session.close()


@asynccontextmanager
async def async_session_scope(*, commit: bool = False) -> AsyncIterator[AsyncSession]:
    """Yield an :class:`AsyncSession` and ensure it is closed.

    Parameters
    ----------
    commit:
        When ``True`` the session is committed on successful exit. Any
        exception triggers an async rollback before the exception is
        re-raised.
    """

    session = SessionLocal(async_session=True)
    try:
        yield session
        if commit:
            await session.commit()
    except BaseException:
        with suppress(Exception):
            await session.rollback()
        raise
    finally:
        with suppress(Exception):
            await session.close()
