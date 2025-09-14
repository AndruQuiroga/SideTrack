"""Candidate track generation from external services."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

from sidetrack.api.clients.lastfm import LastfmClient
from .listenbrainz import ListenBrainzClient

from .spotify import SpotifyService


@dataclass
class Candidate:
    """Simple container for recommendation candidates."""

    spotify_id: str | None = None
    isrc: str | None = None
    artist: str | None = None
    title: str | None = None
    source: str = ""
    score_cf: float = 0.0
    recording_mbid: str | None = None
    seeds: dict[str, set[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""

        return {
            **asdict(self, dict_factory=dict),
            "seeds": {k: sorted(v) for k, v in self.seeds.items()},
        }


def _make_candidate(**kwargs: Any) -> Candidate:
    """Return a :class:`Candidate` with normalised seeds."""

    seeds = kwargs.pop("seeds", {}) or {}
    norm_seeds: dict[str, set[str]] = {}
    for key, val in seeds.items():
        if isinstance(val, (list, set, tuple)):
            norm_seeds[key] = {str(v) for v in val if v}
        elif val:
            norm_seeds[key] = {str(val)}
    return Candidate(seeds=norm_seeds, **kwargs)


def _dedupe(cands: Iterable[Candidate]) -> list[Candidate]:
    """Deduplicate ``cands`` and merge seeds/metadata."""

    by_mbid: dict[str, Candidate] = {}
    by_isrc: dict[str, Candidate] = {}
    by_spotify: dict[str, Candidate] = {}
    by_at: dict[tuple[str | None, str | None], Candidate] = {}
    out: list[Candidate] = []

    for cand in cands:
        existing: Candidate | None = None
        if cand.recording_mbid:
            existing = by_mbid.get(cand.recording_mbid)
        if existing is None and cand.isrc:
            existing = by_isrc.get(cand.isrc)
        if existing is None and cand.spotify_id:
            existing = by_spotify.get(cand.spotify_id)
        if existing is None:
            key = (cand.artist, cand.title)
            existing = by_at.get(key)

        if existing is None:
            out.append(cand)
            if cand.recording_mbid:
                by_mbid[cand.recording_mbid] = cand
            if cand.isrc:
                by_isrc[cand.isrc] = cand
            if cand.spotify_id:
                by_spotify[cand.spotify_id] = cand
            by_at[(cand.artist, cand.title)] = cand
            continue

        for k, v in cand.seeds.items():
            existing.seeds.setdefault(k, set()).update(v)
        if cand.score_cf > existing.score_cf:
            existing.score_cf = cand.score_cf
        if cand.isrc and not existing.isrc:
            existing.isrc = cand.isrc
            by_isrc[cand.isrc] = existing
        if cand.recording_mbid and not existing.recording_mbid:
            existing.recording_mbid = cand.recording_mbid
            by_mbid[cand.recording_mbid] = existing
        if cand.spotify_id and not existing.spotify_id:
            existing.spotify_id = cand.spotify_id
            by_spotify[cand.spotify_id] = existing

    return out


async def _spotify_candidates(sp: SpotifyService) -> list[Candidate]:
    """Generate candidate tracks for a Spotify user."""

    top_tracks = await sp.get_top_items("tracks")
    top_artists = await sp.get_top_items("artists")
    seed_tracks = [t.get("id") for t in top_tracks if t.get("id")][:5]
    seed_artists = [a.get("id") for a in top_artists if a.get("id")][:5]
    seeds = {"tracks": seed_tracks, "artists": seed_artists}

    recs = await sp.get_recommendations(seeds)

    recent_ids = {
        (item.get("track") or {}).get("id")
        for item in await sp.get_recently_played()
        if (item.get("track") or {}).get("id")
    }
    saved_ids = {
        (item.get("track") or {}).get("id")
        for item in await sp.get_saved_tracks()
        if (item.get("track") or {}).get("id")
    }
    seen = recent_ids | saved_ids

    out: list[Candidate] = []
    for track in recs:
        tid = track.get("id")
        if not tid or tid in seen:
            continue
        out.append(
            _make_candidate(
                spotify_id=tid,
                isrc=(track.get("external_ids") or {}).get("isrc"),
                artist=", ".join(a.get("name") for a in track.get("artists", [])),
                title=track.get("name"),
                seeds=seeds,
                source="spotify",
                score_cf=float(track.get("popularity", 0)) / 100.0,
            )
        )
    return _dedupe(out)


async def _lastfm_candidates(lfm: LastfmClient, user: str) -> list[Candidate]:
    """Generate candidate tracks for a Last.fm user."""

    out: list[Candidate] = []

    top_tracks = await lfm.get_top_tracks(user)
    for tr in top_tracks[:5]:
        artist_name = (tr.get("artist") or {}).get("name")
        track_name = tr.get("name")
        if not artist_name or not track_name:
            continue
        sims = await lfm.get_similar_track(artist=artist_name, track=track_name)
        for s in sims:
            cand = _make_candidate(
                artist=(s.get("artist") or {}).get("name"),
                title=s.get("name"),
                seeds={"artist": artist_name, "track": track_name},
                source="lastfm",
                score_cf=float(s.get("match") or 0.0),
            )
            if cand.artist and cand.title:
                out.append(cand)

    top_artists = await lfm.get_top_artists(user)
    for art in top_artists[:5]:
        name = art.get("name")
        if not name:
            continue
        sims = await lfm.get_similar_artist(name=name)
        for sa in sims:
            sname = sa.get("name")
            if not sname:
                continue
            tracks = await lfm.get_artist_top_tracks(sname, limit=1)
            track = tracks[0] if tracks else None
            title = track.get("name") if isinstance(track, dict) else None
            if not title:
                continue
            out.append(
                _make_candidate(
                    artist=sname,
                    title=title,
                    seeds={"artist": name},
                    source="lastfm",
                    score_cf=float(sa.get("match") or 0.0),
                )
            )
    return _dedupe(out)


async def _listenbrainz_candidates(lb: ListenBrainzClient, user: str) -> list[Candidate]:
    """Generate candidate tracks for a ListenBrainz user."""

    out: list[Candidate] = []
    recs = await lb.get_cf_recommendations(user)
    for r in recs:
        out.append(
            _make_candidate(
                artist=r.get("artist_name"),
                title=r.get("recording_name"),
                recording_mbid=r.get("recording_mbid"),
                seeds={"user": user},
                source="listenbrainz",
                score_cf=float(r.get("score") or 0.0),
            )
        )
    return _dedupe(out)


async def generate_candidates(
    *,
    spotify: SpotifyService | None = None,
    lastfm: LastfmClient | None = None,
    lastfm_user: str | None = None,
    listenbrainz: ListenBrainzClient | None = None,
    listenbrainz_user: str | None = None,
) -> list[dict[str, Any]]:
    """Return recommendation candidates for the given user."""

    tasks = []
    if spotify is not None:
        tasks.append(_spotify_candidates(spotify))
    if lastfm is not None and lastfm_user:
        tasks.append(_lastfm_candidates(lastfm, lastfm_user))
    if listenbrainz is not None and listenbrainz_user:
        tasks.append(_listenbrainz_candidates(listenbrainz, listenbrainz_user))
    if not tasks:
        return []

    results = await asyncio.gather(*tasks)
    merged: list[Candidate] = []
    for cands in results:
        merged.extend(cands)
    return [c.to_dict() for c in _dedupe(merged)]
