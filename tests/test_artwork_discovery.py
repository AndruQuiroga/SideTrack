"""Synthetic provider metadata, bounded transport and honest discovery gaps."""

import socket

import httpx
import pytest

from sidetrack.external import artwork
from sidetrack.external.artwork import ArtworkError, Discovery, image_url, spotify_entity

pytestmark = pytest.mark.unit
ENTITY = "A" * 22
IMAGE = "https://i.scdn.co/image/synthetic"
TARGET = {
    "kind": "song",
    "id": "00000000-0000-0000-0000-000000000001",
    "title": "Synthetic Song",
    "artist_name": "Synthetic Band",
    "cover_url": None,
    "url": f"https://open.spotify.com/track/{ENTITY}",
}


@pytest.fixture
def public_dns(monkeypatch):
    monkeypatch.setattr(artwork, "public_host", lambda host: None)
    monkeypatch.setattr(artwork.spotify, "_auth_headers", lambda: {})


def client(handler):
    return Discovery(httpx.Client(transport=httpx.MockTransport(handler)))


def metadata():
    return {
        "id": ENTITY,
        "type": "track",
        "name": TARGET["title"],
        "artists": [{"name": TARGET["artist_name"]}],
        "album": {"images": [{"url": IMAGE}]},
    }


def test_exact_link_validates_metadata_image_and_deduplicates(public_dns):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.host == "api.spotify.com":
            return httpx.Response(200, json=metadata())
        return httpx.Response(
            200, content=b"\xff\xd8\xffsynthetic", headers={"content-type": "image/jpeg"}
        )

    d = client(handler)
    first = d.discover(TARGET)
    assert first["status"] == "ready"
    assert first["cover_url"] == IMAGE
    assert d.discover(TARGET) == first
    assert len(calls) == 2


def test_conflicting_exact_identity_never_fetches_image(public_dns):
    def handler(request):
        assert request.url.host == "api.spotify.com"
        return httpx.Response(200, json={**metadata(), "name": "Different Song"})

    assert client(handler).discover(TARGET)["status"] == "conflict"


def test_ambiguous_album_editions_and_missing_song_identity(public_dns):
    album = {**TARGET, "kind": "album", "url": None}
    matches = [
        {"id": letter * 22, "name": TARGET["title"], "artists": [{"name": TARGET["artist_name"]}]}
        for letter in "AB"
    ]
    d = client(lambda r: httpx.Response(200, json={"albums": {"items": matches}}))
    assert d.discover(album)["status"] == "unresolved"
    assert d.discover({**TARGET, "url": None})["status"] == "unresolved"


@pytest.mark.parametrize(
    "url",
    [
        "http://i.scdn.co/image/a",
        "https://127.0.0.1/a",
        "https://i.scdn.co.evil.test/a",
        "https://user:password@i.scdn.co/a",
        "https://i.scdn.co:444/a",
        "https://i.scdn.co/a?secret=x",
    ],
)
def test_unsafe_image_url(url):
    with pytest.raises(ArtworkError):
        image_url(url)


def test_redirect_is_checked_before_following(public_dns):
    calls = []

    def handler(request):
        calls.append(request.url.host)
        return httpx.Response(302, headers={"location": "http://169.254.169.254/"})

    with pytest.raises(ArtworkError, match="Unapproved"):
        client(handler).validate_image(IMAGE)
    assert calls == ["i.scdn.co"]


@pytest.mark.parametrize(
    "body,headers",
    [
        (b"<html>not art</html>", {"content-type": "text/html"}),
        (b"not jpeg", {"content-type": "image/jpeg"}),
        (b"\xff\xd8\xff" + b"a" * artwork.MAX_BYTES, {"content-type": "image/jpeg"}),
    ],
    ids=["html", "invalid-jpeg", "oversized"],
)
def test_bad_or_oversized_images(public_dns, body, headers):
    with pytest.raises(ArtworkError):
        client(lambda r: httpx.Response(200, content=body, headers=headers)).validate_image(IMAGE)


def test_retry_budget_and_timeout(public_dns, monkeypatch):
    calls = []
    monkeypatch.setattr(artwork.time, "sleep", lambda delay: None)

    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={"retry-after": "0"})

    assert client(handler).discover(TARGET)["status"] == "unavailable"
    assert len(calls) == 3

    def timeout(request):
        raise httpx.ReadTimeout("private response must not be logged")

    result = client(timeout).discover(TARGET)
    assert result["status"] == "unavailable"
    assert "private" not in str(result)


def test_private_dns_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(ArtworkError, match="not public"):
        artwork.public_host("i.scdn.co")


def test_reviewed_musicbrainz_identity(public_dns, monkeypatch):
    from sidetrack.external import musicbrainz

    monkeypatch.setattr(
        musicbrainz,
        "get_release_group",
        lambda _: {"title": TARGET["title"], "artist-credit": [{"name": TARGET["artist_name"]}]},
    )
    d = client(
        lambda r: httpx.Response(
            200, content=b"\xff\xd8\xfftest", headers={"content-type": "image/jpeg"}
        )
    )
    result = d.discover(
        {**TARGET, "kind": "album", "url": None},
        {"musicbrainz_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert result["status"] == "ready"


def test_spotify_link_host_and_kind_are_exact():
    assert spotify_entity(TARGET["url"] + "?si=public") == ("track", ENTITY)
    with pytest.raises(ArtworkError):
        spotify_entity("https://evil.test/track/" + ENTITY)


def test_oembed_requires_independent_reviewed_identity(public_dns, monkeypatch):
    monkeypatch.setattr(
        artwork.spotify, "_auth_headers", lambda: (_ for _ in ()).throw(RuntimeError())
    )

    def handler(request):
        if request.url.path == "/oembed":
            return httpx.Response(200, json={"title": TARGET["title"], "thumbnail_url": IMAGE})
        return httpx.Response(
            200, content=b"\xff\xd8\xffimage", headers={"content-type": "image/jpeg"}
        )

    d = client(handler)
    assert d.discover(TARGET)["status"] == "unavailable"
    review = {
        "verified_identity": {
            "url": TARGET["url"],
            "title": TARGET["title"],
            "artist_name": TARGET["artist_name"],
            "reason": "Synthetic independently checked artist and title",
            "evidence_digest": "c" * 64,
        }
    }
    assert d.discover(TARGET, review)["status"] == "ready"
    review["verified_identity"]["artist_name"] = "Wrong Artist"
    assert d.discover(TARGET, review)["status"] == "unavailable"
