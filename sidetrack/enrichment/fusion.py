from __future__ import annotations

"""Utilities for merging tag data from multiple sources.

This module provides helpers for combining Last.fm and MusicBrainz tag data
into a canonical tag space and for deriving aggregate information such as
TF–IDF scores or label rollups.  The functions are intentionally lightweight so
that they can be reused in both batch jobs and API handlers.
"""

from collections import Counter
import math
from typing import Iterable, Mapping

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import MBLabel, MBTag


def canonicalize_tag(tag: str) -> str:
    """Return a normalised representation of *tag*.

    The canonicalisation here is deliberately conservative: tags are converted
    to lowercase and stripped of surrounding whitespace; hyphens are treated as
    spaces.  This is sufficient for the small, controlled vocabularies used in
    tests while remaining predictable for callers.
    """

    return tag.strip().lower().replace("-", " ")


def merge_tags(
    lastfm: Mapping[str, int] | None, mb: Mapping[str, int] | Iterable[str] | None
) -> dict[str, int]:
    """Merge tag counts from Last.fm and MusicBrainz.

    ``lastfm`` is expected to be a mapping of tag → play-count as returned by
    :class:`~sidetrack.api.clients.lastfm.LastfmClient`.  ``mb`` may be either a
    mapping or an iterable of tag names.  Tags from both sources are
    canonicalised before being combined.
    """

    counts: Counter[str] = Counter()

    def _add(src: Mapping[str, int] | Iterable[str] | None) -> None:
        if not src:
            return
        if isinstance(src, Mapping):
            items = src.items()
        else:
            items = ((t, 1) for t in src)
        for tag, cnt in items:
            key = canonicalize_tag(str(tag))
            if key:
                counts[key] += int(cnt)

    _add(lastfm)
    _add(mb)
    return dict(counts)


def compute_user_tfidf(
    user_tags: Mapping[str, int], all_user_tags: Iterable[Mapping[str, int]]
) -> dict[str, float]:
    """Compute TF–IDF weights for ``user_tags``.

    ``user_tags`` contains raw tag counts for a single user.  ``all_user_tags``
    is an iterable of tag-count mappings for every user in the population,
    including the current one.  Both inputs are canonicalised prior to
    calculation.  The returned dictionary maps canonical tag names to TF–IDF
    scores.
    """

    total_docs = 0
    doc_freq: Counter[str] = Counter()
    for tags in all_user_tags:
        total_docs += 1
        seen = set()
        for tag in tags:
            key = canonicalize_tag(tag)
            if key:
                seen.add(key)
        doc_freq.update(seen)

    total_terms = sum(user_tags.values()) or 1
    scores: dict[str, float] = {}
    for tag, cnt in user_tags.items():
        key = canonicalize_tag(tag)
        if not key:
            continue
        tf = cnt / total_terms
        df = doc_freq.get(key, 0)
        # add-one smoothing to avoid division by zero
        idf = math.log((total_docs or 1) / (1 + df)) + 1.0
        scores[key] = tf * idf
    return scores


def label_rollups(
    labels: Iterable[Mapping[str, str | None]], release_year: int | None
) -> dict[str, str | None]:
    """Derive simple label-based rollups.

    ``labels`` should be an iterable of dictionaries with optional ``name`` and
    ``country`` keys describing MusicBrainz labels.  ``release_year`` is used to
    bucket a recording into coarse era bins.  The function returns a mapping
    with ``primary_label``, ``label_country`` and ``era`` keys.
    """

    primary_label = None
    label_country = None
    for lab in labels:
        primary_label = lab.get("name") or primary_label
        label_country = lab.get("country") or label_country
        if primary_label and label_country:
            break

    era = None
    if release_year:
        if 1990 <= release_year < 2000:
            era = "90s"
        elif 2000 <= release_year < 2010:
            era = "00s"
        elif 2010 <= release_year < 2020:
            era = "10s"
        elif 2020 <= release_year < 2030:
            era = "20s"

    return {
        "primary_label": primary_label,
        "label_country": label_country,
        "era": era,
    }


async def persist_mb_tags(
    db: AsyncSession, track_id: int, tags: Mapping[str, float]
) -> None:
    """Persist tag scores for a track to the ``mb_tag`` table."""

    await db.execute(delete(MBTag).where(MBTag.track_id == track_id))
    for tag, score in tags.items():
        db.add(MBTag(track_id=track_id, tag=tag, score=float(score)))
    await db.commit()


async def persist_mb_label(
    db: AsyncSession, track_id: int, rollup: Mapping[str, str | None]
) -> None:
    """Persist label rollup information to the ``mb_label`` table."""

    await db.execute(delete(MBLabel).where(MBLabel.track_id == track_id))
    db.add(
        MBLabel(
            track_id=track_id,
            primary_label=rollup.get("primary_label"),
            label_country=rollup.get("label_country"),
            era=rollup.get("era"),
        )
    )
    await db.commit()
