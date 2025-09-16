import pytest

from sidetrack.api.config import Settings
from sidetrack.common.models import UserSettings
from sidetrack.services.maintenance import ingest_listens


class StubDBResult:
    def __init__(self, row: UserSettings | None) -> None:
        self._row = row

    def scalar_one_or_none(self) -> UserSettings | None:
        return self._row


class StubDB:
    def __init__(self, row: UserSettings | None) -> None:
        self._row = row

    async def execute(self, *_args, **_kwargs) -> StubDBResult:
        return StubDBResult(self._row)


class StubListenService:
    def __init__(self) -> None:
        self.calls: list[str | None] = []

    async def ingest_lb_rows(
        self, listens: list[dict], user_id: str | None = None, *, source: str | None = None
    ) -> int:
        self.calls.append(user_id)
        return len(listens)


class StubListenBrainzClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    async def fetch_listens(
        self, user: str, since, token: str | None, limit: int = 500
    ) -> list[dict]:  # pragma: no cover - signature mirrors real client
        self.calls.append((user, token))
        return [{}]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_ingest_listens_prefers_user_credentials():
    row = UserSettings(
        user_id="u1",
        listenbrainz_user="alice",
        listenbrainz_token="user-token",
    )
    db = StubDB(row)
    settings = Settings(listenbrainz_token="global-token", listenbrainz_user="global-user")
    listen_service = StubListenService()
    lb_client = StubListenBrainzClient()

    result = await ingest_listens(
        db=db,
        listen_service=listen_service,
        user_id="u1",
        settings=settings,
        source="listenbrainz",
        lb_client=lb_client,
        fallback_to_sample=False,
    )

    assert result.ingested == 1
    assert result.source == "listenbrainz"
    assert lb_client.calls == [("alice", "user-token")]
    assert listen_service.calls == ["u1"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_ingest_listens_falls_back_to_settings():
    row = UserSettings(user_id="u2")
    db = StubDB(row)
    settings = Settings(listenbrainz_token="global-token", listenbrainz_user="global-user")
    listen_service = StubListenService()
    lb_client = StubListenBrainzClient()

    result = await ingest_listens(
        db=db,
        listen_service=listen_service,
        user_id="u2",
        settings=settings,
        source="listenbrainz",
        lb_client=lb_client,
        fallback_to_sample=False,
    )

    assert result.ingested == 1
    assert result.source == "listenbrainz"
    assert lb_client.calls == [("global-user", "global-token")]
    assert listen_service.calls == ["u2"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_ingest_listens_handles_missing_credentials():
    settings = Settings(listenbrainz_user=None, listenbrainz_token=None)
    listen_service = StubListenService()
    lb_client = StubListenBrainzClient()
    db = StubDB(None)

    result = await ingest_listens(
        db=db,
        listen_service=listen_service,
        user_id="u3",
        settings=settings,
        source="listenbrainz",
        lb_client=lb_client,
        fallback_to_sample=False,
    )

    assert result.ingested == 1
    assert result.source == "listenbrainz"
    assert lb_client.calls == [("u3", None)]
    assert listen_service.calls == ["u3"]
