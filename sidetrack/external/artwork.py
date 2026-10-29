"""Bounded artwork discovery. Never fetch audio, arbitrary URLs or provider HTML."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
import time
import unicodedata
from typing import Any, cast
from urllib.parse import urljoin, urlsplit
from uuid import UUID

import httpx

from . import spotify
from .http import ExternalApiError

MAX_BYTES = 5 * 1024 * 1024
IMAGE_HOSTS = frozenset(
    {
        "i.scdn.co",
        "image-cdn-fa.spotifycdn.com",
        "image-cdn-ak.spotifycdn.com",
        "coverartarchive.org",
        "archive.org",
    }
)


class ArtworkError(ValueError):
    """Safe operator-facing diagnostic, never a URL or provider response body."""


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def spotify_entity(url: str) -> tuple[str, str]:
    parsed = urlsplit(url)
    match = re.fullmatch(r"/(album|track)/([A-Za-z0-9]{22})/?", parsed.path)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "open.spotify.com"
        or not match
        or parsed.fragment
    ):
        raise ArtworkError("Unsupported Spotify entity link.")
    return match[1], match[2]


def image_url(url: str) -> str:
    """Syntactic allowlist, also used during offline application and API reads."""
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    archive_host = bool(re.fullmatch(r"ia[0-9]+\.(?:us|eu)\.archive\.org", host))
    if (
        parsed.scheme != "https"
        or (host not in IMAGE_HOSTS and not archive_host)
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or not parsed.path
    ):
        raise ArtworkError("Unapproved artwork destination.")
    return url


def public_host(host: str) -> None:
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ArtworkError("Artwork destination is not public.")
    except OSError:
        raise ArtworkError("Artwork destination cannot be resolved.") from None


class Discovery:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=15, follow_redirects=False, trust_env=False)
        self.cache: dict[str, Any] = {}

    def close(self) -> None:
        self.client.close()

    def json(self, url: str, *, params=None, headers=None) -> dict:
        key = digest([url, params])
        if key in self.cache:
            return cast(dict, self.cache[key])
        # Callers construct only fixed provider endpoints. Never accept this URL from a plan.
        try:
            for attempt in range(3):
                with self.client.stream("GET", url, params=params, headers=headers) as response:
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt == 2:
                            raise ArtworkError("Provider retry budget exhausted.")
                        try:
                            delay = float(response.headers.get("Retry-After", "1"))
                        except ValueError:
                            delay = 1
                        if not 0 <= delay <= 10:
                            raise ArtworkError("Provider requires a later retry.")
                        time.sleep(delay)
                        continue
                    if response.status_code != 200:
                        raise ArtworkError("Provider metadata unavailable.")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_BYTES:
                            raise ArtworkError("Provider response exceeds size limit.")
                    result = json.loads(body)
                    if not isinstance(result, dict):
                        raise ArtworkError("Invalid provider metadata.")
                    self.cache[key] = result
                    return result
        except (httpx.HTTPError, json.JSONDecodeError):
            raise ArtworkError("Provider metadata unavailable.") from None
        raise ArtworkError("Provider metadata unavailable.")

    def validate_image(self, url: str) -> dict:
        key = "image:" + url
        if key in self.cache:
            return cast(dict, self.cache[key])
        current = url
        try:
            for _ in range(5):
                image_url(current)
                public_host(urlsplit(current).hostname or "")
                with self.client.stream("GET", current) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        current = urljoin(current, response.headers.get("Location", ""))
                        continue
                    if response.status_code != 200:
                        raise ArtworkError("Artwork image unavailable.")
                    content_type = response.headers.get("Content-Type", "").split(";")[0]
                    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
                        raise ArtworkError("Artwork response is not a supported image.")
                    size = 0
                    sha = hashlib.sha256()
                    prefix = b""
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise ArtworkError("Artwork exceeds size limit.")
                        prefix = (prefix + chunk)[:12]
                        sha.update(chunk)
                    valid = (
                        (content_type == "image/jpeg" and prefix.startswith(b"\xff\xd8\xff"))
                        or (content_type == "image/png" and prefix.startswith(b"\x89PNG\r\n\x1a\n"))
                        or (
                            content_type == "image/webp"
                            and prefix.startswith(b"RIFF")
                            and prefix[8:12] == b"WEBP"
                        )
                    )
                    if not valid:
                        raise ArtworkError("Artwork image signature is invalid.")
                    result = {"cover_url": current, "image_sha256": sha.hexdigest(), "bytes": size}
                    self.cache[key] = result
                    return result
        except httpx.HTTPError:
            raise ArtworkError("Artwork image unavailable.") from None
        raise ArtworkError("Artwork redirect limit exceeded.")

    def spotify(self, kind: str, entity_id: str) -> dict:
        if kind not in {"track", "album"} or not re.fullmatch(r"[A-Za-z0-9]{22}", entity_id):
            raise ArtworkError("Invalid Spotify identity.")
        try:
            headers = spotify._auth_headers()
        except (RuntimeError, httpx.HTTPError):
            raise ArtworkError("Spotify metadata credentials unavailable.") from None
        data = self.json(f"https://api.spotify.com/v1/{kind}s/{entity_id}", headers=headers)
        if data.get("id") != entity_id or data.get("type") != kind:
            raise ArtworkError("Provider entity identity changed.")
        images = (data.get("album", {}) if kind == "track" else data).get("images") or []
        cover = images[0].get("url") if images else None
        canonical = f"https://open.spotify.com/{kind}/{entity_id}"
        if not cover:
            cover = self.json("https://open.spotify.com/oembed", params={"url": canonical}).get(
                "thumbnail_url"
            )
        return {
            "title": data.get("name"),
            "artist_name": ", ".join(a["name"] for a in data.get("artists", [])),
            "provider_url": canonical,
            "cover_url": cover,
            "year": int(data.get("release_date", "0000")[:4]) or None,
        }

    def discover(self, target: dict, review: dict | None = None) -> dict:
        """Return a candidate or an explicit gap. Review can select identities, never images."""
        result = {"target": target, "status": "unavailable"}
        if target.get("cover_url"):
            return {**result, "status": "existing"}
        review = review or {}
        try:
            link = target.get("url") or review.get("spotify_url")
            mbid = target.get("musicbrainz_id") or review.get("musicbrainz_id")
            if link:
                kind, entity_id = spotify_entity(link)
                if kind != ("album" if target["kind"] == "album" else "track"):
                    raise ArtworkError("Provider entity kind conflicts with target.")
                try:
                    candidate = self.spotify(kind, entity_id)
                except ArtworkError:
                    reviewed = review.get("verified_identity", {})
                    canonical = f"https://open.spotify.com/{kind}/{entity_id}"
                    if (
                        reviewed.get("url") != canonical
                        or not reviewed.get("reason")
                        or not re.fullmatch(r"[a-f0-9]{64}", reviewed.get("evidence_digest", ""))
                        or any(
                            normalize(reviewed.get(k, "")) != normalize(target[k])
                            for k in ("title", "artist_name")
                        )
                    ):
                        raise
                    embed = self.json("https://open.spotify.com/oembed", params={"url": canonical})
                    if normalize(embed.get("title", "")) != normalize(target["title"]):
                        raise ArtworkError("oEmbed title conflicts with reviewed identity.")
                    candidate = {
                        "title": reviewed["title"],
                        "artist_name": reviewed["artist_name"],
                        "provider_url": canonical,
                        "cover_url": embed.get("thumbnail_url"),
                        "review_evidence_digest": reviewed["evidence_digest"],
                    }
            elif mbid:
                # A reviewed MBID is required; never choose an arbitrary release group.
                mbid = str(UUID(mbid))
                from .musicbrainz import get_release_group

                data = get_release_group(mbid)
                candidate = {
                    "title": data.get("title"),
                    "artist_name": ", ".join(
                        a.get("name") or a.get("artist", {}).get("name", "")
                        for a in data.get("artist-credit", data.get("artist_credit", []))
                        if isinstance(a, dict)
                    ),
                    "provider_url": f"https://musicbrainz.org/release-group/{mbid}",
                    "cover_url": f"https://coverartarchive.org/release-group/{mbid}/front-500",
                }
            elif target["kind"] == "album":
                try:
                    headers = spotify._auth_headers()
                except (RuntimeError, httpx.HTTPError):
                    raise ArtworkError("Spotify metadata credentials unavailable.") from None
                data = self.json(
                    "https://api.spotify.com/v1/search",
                    params={
                        "q": f'album:{target["title"]} artist:{target["artist_name"]}',
                        "type": "album",
                        "limit": "10",
                    },
                    headers=headers,
                )
                matches = []
                for item in data.get("albums", {}).get("items", []):
                    artist = ", ".join(a["name"] for a in item.get("artists", []))
                    if normalize(item["name"]) != normalize(target["title"]):
                        continue
                    if normalize(artist) != normalize(target["artist_name"]):
                        continue
                    year = target.get("release_year")
                    if year and item.get("release_date", "")[:4] != str(year):
                        continue
                    matches.append(item["id"])
                if len(set(matches)) != 1:
                    return {**result, "status": "unresolved", "reason": "No unique exact match."}
                candidate = self.spotify("album", matches[0])
            else:
                return {**result, "status": "unresolved", "reason": "Exact song identity needed."}
            if any(
                normalize(candidate.get(key) or "") != normalize(target[key])
                for key in ("title", "artist_name")
            ):
                return {**result, "status": "conflict", "reason": "Provider identity mismatch."}
            if not candidate.get("cover_url"):
                raise ArtworkError("No artwork reported by provider.")
            image = self.validate_image(candidate["cover_url"])
            return {
                **result,
                "status": "ready",
                "provider_url": candidate["provider_url"],
                **image,
                "evidence_digest": digest(candidate),
            }
        except (ArtworkError, ExternalApiError, ValueError, KeyError, TypeError, httpx.HTTPError):
            return {**result, "reason": "Artwork or verified provider identity unavailable."}
