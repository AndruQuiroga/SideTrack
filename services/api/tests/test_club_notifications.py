"""Authenticated claims, bounded delivery retries and fenced acknowledgments."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from sidetrack.club import Notification, Week, produce_notification, reconcile_week
from sidetrack.queue_models import JobSchedule


@pytest.fixture
def pending_event(db):
    now = db.scalar(select(func.clock_timestamp()))
    week = Week(
        label="Delivery test",
        nominations_thread_id="123",
        nominations_close_at=now - timedelta(seconds=5),
    )
    db.add(week)
    reconcile_week(db, week)
    schedule = db.get(JobSchedule, f"club:{week.id}:nominations-close")
    produce_notification(db, **schedule.arguments)
    db.flush()
    return db.scalar(select(Notification))


def test_requires_service_auth(anon_client, pending_event):
    assert anon_client.post("/club/notifications/claim").status_code == 401


def test_claim_ack_and_stale_token(client, db, pending_event):
    response = client.post("/club/notifications/claim")
    assert response.status_code == 200
    event = response.json()[0]
    assert event["thread_id"] == "123"
    assert client.post("/club/notifications/claim").json() == []
    url = f"/club/notifications/{event['id']}/ack"
    assert (
        client.post(url, json={"lease_token": str(uuid4()), "message_id": "456"}).status_code == 409
    )
    assert (
        client.post(
            url, json={"lease_token": event["lease_token"], "message_id": "456"}
        ).status_code
        == 204
    )
    assert client.post("/club/notifications/claim").json() == []
    db.refresh(pending_event)
    assert pending_event.state == "sent" and pending_event.message_id == "456"


def test_expired_lease_reclaims_and_fences_old_ack(client, db, pending_event):
    first = client.post("/club/notifications/claim").json()[0]
    pending_event.lease_until -= timedelta(minutes=2)
    db.commit()
    second = client.post("/club/notifications/claim").json()[0]
    assert second["lease_token"] != first["lease_token"]
    response = client.post(
        f"/club/notifications/{first['id']}/ack",
        json={
            "lease_token": first["lease_token"],
            "message_id": "456",
        },
    )
    assert response.status_code == 409


def test_backoff_and_exhaustion(client, db, pending_event):
    for attempt in range(3):
        event = client.post("/club/notifications/claim").json()[0]
        response = client.post(
            f"/club/notifications/{event['id']}/fail",
            json={
                "lease_token": event["lease_token"],
                "retry_after": 10,
            },
        )
        assert response.status_code == 204
        assert client.post("/club/notifications/claim").json() == []
        db.refresh(pending_event)
        if attempt < 2:
            assert pending_event.state == "pending"
            pending_event.next_attempt_at -= timedelta(minutes=10)
            db.commit()
    assert pending_event.state == "failed"


def test_permanent_failure_is_visible(client, db, pending_event):
    event = client.post("/club/notifications/claim").json()[0]
    assert (
        client.post(
            f"/club/notifications/{event['id']}/fail",
            json={
                "lease_token": event["lease_token"],
                "permanent": True,
            },
        ).status_code
        == 204
    )
    db.refresh(pending_event)
    assert pending_event.state == "failed"
    assert pending_event.error == "delivery_unavailable"


def test_parallel_clients_cannot_claim_same_event(engine):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete
    from sqlalchemy.orm import Session

    from sidetrack.club import claim_notifications

    with Session(engine) as db, db.begin():
        now = db.scalar(select(func.clock_timestamp()))
        week = Week(
            label="Parallel delivery",
            nominations_thread_id="123",
            nominations_close_at=now - timedelta(seconds=1),
        )
        db.add(week)
        reconcile_week(db, week)
        week_id = week.id
        produce_notification(
            db, **db.get(JobSchedule, f"club:{week.id}:nominations-close").arguments
        )
    barrier = Barrier(2)

    def claim(_):
        with Session(engine) as db, db.begin():
            barrier.wait(timeout=5)
            return len(claim_notifications(db))

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(claim, range(2))) == [0, 1]
    finally:
        with engine.begin() as conn:
            conn.execute(delete(JobSchedule).where(JobSchedule.id.like(f"club:{week_id}:%")))
            conn.execute(delete(Week).where(Week.id == week_id))
