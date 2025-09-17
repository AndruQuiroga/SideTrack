import pytest

from sidetrack.common.models import UserLabel

from tests.factories import TrackFactory


@pytest.mark.asyncio
async def test_list_labels_returns_only_current_user(async_client, async_session):
    track = TrackFactory()
    async_session.add(track)
    await async_session.flush()

    label_one = UserLabel(user_id="alice", track_id=track.track_id, axis="energy", value=0.8)
    label_two = UserLabel(user_id="alice", track_id=track.track_id, axis="valence", value=0.2)
    other_label = UserLabel(user_id="bob", track_id=track.track_id, axis="energy", value=0.1)

    async_session.add_all([label_one, label_two, other_label])
    await async_session.flush()
    label_ids = {label_one.id, label_two.id}
    await async_session.commit()

    resp = await async_client.get("/labels", headers={"X-User-Id": "alice"})
    assert resp.status_code == 200
    payload = resp.json()

    assert {item["id"] for item in payload["labels"]} == label_ids
    assert all(item["user_id"] == "alice" for item in payload["labels"])
    assert all("created_at" in item for item in payload["labels"])
    assert payload["labels"][0]["id"] == max(label_ids)


@pytest.mark.asyncio
async def test_list_labels_requires_auth(async_client):
    resp = await async_client.get("/labels")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_label_removes_row(async_client, async_session):
    track = TrackFactory()
    async_session.add(track)
    await async_session.flush()

    label = UserLabel(user_id="alice", track_id=track.track_id, axis="energy", value=0.7)
    async_session.add(label)
    await async_session.flush()
    label_id = label.id
    await async_session.commit()

    resp = await async_client.delete(f"/labels/{label_id}", headers={"X-User-Id": "alice"})
    assert resp.status_code == 200
    assert resp.json() == {"detail": "deleted", "id": label_id}

    await async_session.expire_all()
    remaining = await async_session.get(UserLabel, label_id)
    assert remaining is None


@pytest.mark.asyncio
async def test_delete_label_validates_ownership(async_client, async_session):
    track = TrackFactory()
    async_session.add(track)
    await async_session.flush()

    label = UserLabel(user_id="alice", track_id=track.track_id, axis="energy", value=0.5)
    async_session.add(label)
    await async_session.flush()
    label_id = label.id
    await async_session.commit()

    resp = await async_client.delete(f"/labels/{label_id}", headers={"X-User-Id": "mallory"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Label not found"

    await async_session.expire_all()
    still_there = await async_session.get(UserLabel, label_id)
    assert still_there is not None


@pytest.mark.asyncio
async def test_delete_label_requires_auth(async_client):
    resp = await async_client.delete("/labels/123")
    assert resp.status_code == 401
