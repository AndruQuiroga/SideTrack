"""Candidate track generation from Spotify or Last.fm histories."""

from __future__ import annotations

from typing import Any

from .lastfm import LastfmService
from .spotify import SpotifyService


async def _spotify_candidates(sp: SpotifyService) -> list[dict[str, Any]]:
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

    out: list[dict[str, Any]] = []
    for track in recs:
        tid = track.get("id")
        if not tid or tid in seen:
            continue
        out.append(
            {
                "spotify_id": tid,
                "isrc": (track.get("external_ids") or {}).get("isrc"),
                "artist": ", ".join(a.get("name") for a in track.get("artists", [])),
                "title": track.get("name"),
                "seeds": seeds,
                "source": "spotify",
                "score_cf": float(track.get("popularity", 0)) / 100.0,
            }
        )
    return out


async def _lastfm_candidates(lfm: LastfmService, user: str) -> list[dict[str, Any]]:
    """Generate candidate tracks for a Last.fm user."""

    out: list[dict[str, Any]] = []

    top_tracks = await lfm.get_top_tracks(user)
    for tr in top_tracks[:5]:
        artist_name = (tr.get("artist") or {}).get("name")
        track_name = tr.get("name")
        if not artist_name or not track_name:
            continue
        sims = await lfm.get_similar_track(artist=artist_name, track=track_name)
        for s in sims:
            cand = {
                "spotify_id": None,
                "isrc": None,
                "artist": (s.get("artist") or {}).get("name"),
                "title": s.get("name"),
                "seeds": {"artist": artist_name, "track": track_name},
                "source": "lastfm",
                "score_cf": float(s.get("match") or 0.0),
            }
            if cand["artist"] and cand["title"]:
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
                {
                    "spotify_id": None,
                    "isrc": None,
                    "artist": sname,
                    "title": title,
                    "seeds": {"artist": name},
                    "source": "lastfm",
                    "score_cf": float(sa.get("match") or 0.0),
                }
            )
    return out


async def generate_candidates(
    *,
    spotify: SpotifyService | None = None,
    lastfm: LastfmService | None = None,
    lastfm_user: str | None = None,
) -> list[dict[str, Any]]:
    """Return recommendation candidates for the given user."""

    if spotify is not None:
        return await _spotify_candidates(spotify)
    if lastfm is not None and lastfm_user:
        return await _lastfm_candidates(lastfm, lastfm_user)
    return []
