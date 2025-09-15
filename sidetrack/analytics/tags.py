"""Helpers for canonicalising and analysing tag data."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Mapping


def canonicalize_tag(tag: str) -> str:
    """Return a normalised representation of *tag*.

    Tags are converted to lowercase and stripped of surrounding whitespace;
    hyphens are treated as spaces. This conservative approach keeps the helper
    predictable while remaining sufficient for the controlled vocabularies used
    in tests.
    """

    return tag.strip().lower().replace("-", " ")


def merge_tags(
    lastfm: Mapping[str, int] | None, mb: Mapping[str, int] | Iterable[str] | None
) -> dict[str, int]:
    """Merge tag counts from Last.fm and MusicBrainz.

    ``lastfm`` is expected to be a mapping of tag → play-count as returned by
    :class:`~sidetrack.services.lastfm.LastfmClient`. ``mb`` may be either a
    mapping or an iterable of tag names. Tags from both sources are canonicalised
    before being combined.
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
    """Compute TF–IDF weights for ``user_tags``."""

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
    """Derive simple label-based rollups."""

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
