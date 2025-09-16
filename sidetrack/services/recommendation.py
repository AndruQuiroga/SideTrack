"""Unified recommendation services: candidates, ranking, and insights."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Integer, String, Text, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from sidetrack.analytics.tags import canonicalize_tag
from sidetrack.common.models import Base, Listen

from .lastfm import LastfmClient
from .listenbrainz import ListenBrainzClient
from .spotify import SpotifyUserClient

if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    from .musicbrainz import MusicBrainzService


# ---------------------------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------------------------


@dataclass(slots=True)
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


async def _spotify_candidates(sp: SpotifyUserClient) -> list[Candidate]:
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
    spotify: SpotifyUserClient | None = None,
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


# ---------------------------------------------------------------------------
# Ranking helpers
# ---------------------------------------------------------------------------


def artist_or_label(item: dict[str, Any]) -> str | None:
    """Return a key for diversity: artist or label."""

    return item.get("artist_mbid") or item.get("artist") or item.get("label")


async def profile_from_spotify(sp: SpotifyUserClient) -> dict[str, float]:
    """Return a simple audio feature profile for a Spotify user."""

    recent = await sp.get_recently_played()
    ids = [
        (item.get("track") or {}).get("id")
        for item in recent
        if (item.get("track") or {}).get("id")
    ]
    features = await sp.get_audio_features(ids) if ids else []

    tempos = [f.get("tempo") for f in features if isinstance(f.get("tempo"), int | float)]
    valences = [f.get("valence") for f in features if isinstance(f.get("valence"), int | float)]
    energies = [f.get("energy") for f in features if isinstance(f.get("energy"), int | float)]

    def _mean(vals: list[float]) -> float:
        return float(sum(vals) / len(vals)) if vals else 0.0

    return {
        "tempo": _mean(tempos),
        "valence": _mean(valences),
        "energy": _mean(energies),
    }


def mmr_diversity(
    items: list[dict[str, Any]],
    *,
    key: Callable[[dict[str, Any]], str | None] = artist_or_label,
    penalty: float = 0.3,
) -> list[dict[str, Any]]:
    """Penalise consecutive results sharing the same ``key``."""

    seen: dict[str | None, int] = {}
    ordered = sorted(
        items, key=lambda x: x.get("final_score", x.get("score_cf", 0.0)), reverse=True
    )
    out: list[dict[str, Any]] = []
    for item in ordered:
        k = key(item)
        dup_count = seen.get(k, 0)
        if dup_count:
            item["final_score"] = float(
                item.get("final_score", item.get("score_cf", 0.0)) - penalty * dup_count
            )
        else:
            item["final_score"] = float(item.get("final_score", item.get("score_cf", 0.0)))
        seen[k] = dup_count + 1
        out.append(item)
    return out


def rank(candidates: list[dict[str, Any]], user_profile: dict[str, float]) -> list[dict[str, Any]]:
    """Score and rerank ``candidates`` using ``user_profile``."""

    def _clamp(x: float) -> float:
        return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

    for cand in candidates:
        tags = cand.get("tags")
        if isinstance(tags, dict):
            cand["tags"] = {
                canonicalize_tag(tag): val
                for tag, val in tags.items()
                if canonicalize_tag(tag)
            }

        score = float(cand.get("score_cf") or 0.0)
        reasons: list[str] = []
        feats = cand.get("audio_features") or {}
        if feats and user_profile:
            tempo = feats.get("tempo")
            if tempo is not None and user_profile.get("tempo") is not None:
                diff = abs(float(tempo) - float(user_profile["tempo"]))
                score += 0.1 * _clamp(1 - diff / 200.0)
                if diff < 10:
                    reasons.append("tempo")
            for name in ("energy", "valence"):
                val = feats.get(name)
                prof_val = user_profile.get(name)
                if val is not None and prof_val is not None:
                    diff = abs(float(val) - float(prof_val))
                    score += 0.1 * _clamp(1 - diff)
                    if diff < 0.1:
                        reasons.append(name)
        cand["final_score"] = _clamp(score)
        cand["reasons"] = reasons

    ranked = mmr_diversity(candidates)
    ranked.sort(key=lambda x: x["final_score"], reverse=True)
    return ranked


# ---------------------------------------------------------------------------
# Listening insights
# ---------------------------------------------------------------------------


class InsightEvent(Base):
    __tablename__ = "insight_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    type: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSON)
    severity: Mapped[int] = mapped_column(Integer, default=0)


def _canonicalise_details(details: dict | None) -> dict | None:
    """Normalise tag names within ``details`` if present."""

    if not details:
        return details
    tags = details.get("tags")
    if isinstance(tags, dict):
        details["tags"] = {
            canonicalize_tag(tag): score
            for tag, score in tags.items()
            if canonicalize_tag(tag)
        }
    return details


async def compute_weekly_insights(db: AsyncSession, user_id: str) -> Sequence[InsightEvent]:
    """Compute simple weekly insights for a user and persist them."""

    now = datetime.now(UTC)
    since = now - timedelta(days=7)

    total = (
        await db.execute(
            select(func.count())
            .select_from(Listen)
            .where(Listen.user_id == user_id, Listen.played_at >= since)
        )
    ).scalar()

    unique_tracks = (
        await db.execute(
            select(func.count(distinct(Listen.track_id)))
            .select_from(Listen)
            .where(Listen.user_id == user_id, Listen.played_at >= since)
        )
    ).scalar()

    events: list[InsightEvent] = []

    if total:
        details = {"count": int(total)}
        events.append(
            InsightEvent(
                user_id=user_id,
                ts=now,
                type="weekly_listens",
                summary=f"{int(total)} listens this week",
                details=_canonicalise_details(details),
                severity=0,
            )
        )
    if unique_tracks:
        details = {"count": int(unique_tracks)}
        events.append(
            InsightEvent(
                user_id=user_id,
                ts=now,
                type="weekly_unique_tracks",
                summary=f"{int(unique_tracks)} unique tracks this week",
                details=_canonicalise_details(details),
                severity=0,
            )
        )

    if not events:
        return []

    async with db.begin():
        db.add_all(events)

    for evt in events:
        await db.refresh(evt)

    return events


async def get_insights(db: AsyncSession, user_id: str, since: datetime) -> Sequence[InsightEvent]:
    """Return insight events for ``user_id`` since ``since``."""

    rows = (
        await db.execute(
            select(InsightEvent)
            .where(InsightEvent.user_id == user_id, InsightEvent.ts >= since)
            .order_by(InsightEvent.ts.desc())
        )
    ).scalars()
    return list(rows)


# ---------------------------------------------------------------------------
# High-level recommendation orchestration
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RecommendationResult:
    """Container returned by :class:`RecommendationService`."""

    candidates: list[dict[str, Any]]
    enriched: list[dict[str, Any]]
    ranked: list[dict[str, Any]]

    def top(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Return the top ``limit`` ranked candidates (or all when ``None``)."""

        if limit is None:
            return self.ranked
        return self.ranked[:limit]


@dataclass(slots=True)
class RecommendationService:
    """Facade combining candidate generation, enrichment, and ranking."""

    spotify: SpotifyUserClient | None = None
    lastfm: LastfmClient | None = None
    lastfm_user: str | None = None
    listenbrainz: ListenBrainzClient | None = None
    listenbrainz_user: str | None = None
    musicbrainz: "MusicBrainzService" | None = None

    _user_profile: dict[str, float] | None = field(default=None, init=False, repr=False)

    async def generate_candidates(self) -> list[dict[str, Any]]:
        """Generate raw candidates from the configured sources."""

        return await generate_candidates(
            spotify=self.spotify,
            lastfm=self.lastfm,
            lastfm_user=self.lastfm_user,
            listenbrainz=self.listenbrainz,
            listenbrainz_user=self.listenbrainz_user,
        )

    async def enrich_candidates(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Attach MusicBrainz metadata when available."""

        enriched: list[dict[str, Any]] = []
        for cand in candidates:
            item = {
                "artist": cand.get("artist"),
                "title": cand.get("title"),
                "source": cand.get("source"),
                "score_cf": cand.get("score_cf"),
            }
            spotify_id = cand.get("spotify_id")
            isrc = cand.get("isrc")
            rec_mbid = cand.get("recording_mbid")

            if self.musicbrainz is not None and isrc:
                mb = await self.musicbrainz.recording_by_isrc(
                    isrc, title=item.get("title"), artist=item.get("artist")
                )
                item.update(
                    {
                        "recording_mbid": mb.get("recording_mbid") or rec_mbid,
                        "artist_mbid": mb.get("artist_mbid"),
                        "release_year": mb.get("year"),
                        "label": mb.get("label"),
                        "tags": mb.get("tags"),
                    }
                )
            elif rec_mbid:
                item["recording_mbid"] = rec_mbid

            if spotify_id:
                item["spotify_id"] = spotify_id

            enriched.append(item)
        return enriched

    async def _ensure_user_profile(self) -> dict[str, float]:
        if self._user_profile is None:
            if self.spotify is None:
                self._user_profile = {}
            else:
                self._user_profile = await profile_from_spotify(self.spotify)
        return self._user_profile

    async def _attach_audio_features(self, items: list[dict[str, Any]]) -> None:
        if self.spotify is None:
            return
        spotify_ids = [item.get("spotify_id") for item in items if item.get("spotify_id")]
        if not spotify_ids:
            return
        features = await self.spotify.get_audio_features(spotify_ids)
        feat_map = {f.get("id"): f for f in features if f.get("id")}
        for item in items:
            sid = item.get("spotify_id")
            if sid and sid in feat_map:
                item["audio_features"] = feat_map[sid]

    async def rank_candidates(
        self,
        candidates: list[dict[str, Any]],
        *,
        limit: int | None = None,
        user_profile: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        """Rank ``candidates`` returning a new ordered list."""

        working = [dict(item) for item in candidates]
        await self._attach_audio_features(working)
        profile = user_profile if user_profile is not None else await self._ensure_user_profile()
        ranked_items = rank(working, profile or {})
        if limit is not None:
            return ranked_items[:limit]
        return ranked_items

    async def generate_recommendations(
        self,
        *,
        limit: int | None = None,
        include_ranked: bool = True,
        enrich: bool = True,
    ) -> RecommendationResult:
        """High-level helper producing candidates, enriched data and rankings."""

        candidates = await self.generate_candidates()
        enriched = (
            await self.enrich_candidates(candidates) if enrich else [dict(c) for c in candidates]
        )
        ranked: list[dict[str, Any]] = []
        if include_ranked and enriched:
            ranked = await self.rank_candidates(enriched, limit=limit)
        elif include_ranked:
            ranked = []
        return RecommendationResult(candidates=candidates, enriched=enriched, ranked=ranked)
