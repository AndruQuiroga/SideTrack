import pytest

from sidetrack.services import recommendation as rec_mod
from sidetrack.services.recommendation import Candidate, generate_candidates


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_candidates_combines_sources(monkeypatch):
    async def fake_sp(_):
        return [Candidate(spotify_id="sp1", source="spotify")]

    async def fake_lfm(_, __):
        return [
            Candidate(
                recording_mbid="mb1", artist="a1", title="t1", source="lastfm"
            )
        ]

    async def fake_lb(_, __):
        return [
            Candidate(isrc="isrc1", artist="a2", title="t2", source="listenbrainz")
        ]

    monkeypatch.setattr(rec_mod, "_spotify_candidates", fake_sp)
    monkeypatch.setattr(rec_mod, "_lastfm_candidates", fake_lfm)
    monkeypatch.setattr(rec_mod, "_listenbrainz_candidates", fake_lb)

    results = await generate_candidates(
        spotify=object(),
        lastfm=object(),
        lastfm_user="u",
        listenbrainz=object(),
        listenbrainz_user="u",
    )

    assert {r["source"] for r in results} == {"spotify", "lastfm", "listenbrainz"}


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["spotify_id", "isrc", "recording_mbid"])
async def test_generate_candidates_dedupes_by_id(monkeypatch, field):
    async def fake_sp(_):
        return [Candidate(**{field: "id1"}, seeds={"sp": {"x"}}, source="spotify")]

    async def fake_lfm(_, __):
        return [Candidate(**{field: "id1"}, seeds={"lf": {"y"}}, source="lastfm")]

    monkeypatch.setattr(rec_mod, "_spotify_candidates", fake_sp)
    monkeypatch.setattr(rec_mod, "_lastfm_candidates", fake_lfm)
    monkeypatch.setattr(rec_mod, "_listenbrainz_candidates", lambda *_: [])

    results = await generate_candidates(
        spotify=object(), lastfm=object(), lastfm_user="u"
    )

    assert len(results) == 1
    seeds = results[0]["seeds"]
    assert set(seeds) == {"sp", "lf"}
