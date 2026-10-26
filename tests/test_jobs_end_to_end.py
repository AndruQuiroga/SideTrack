"""Opt-in built-image rehearsal with temporary Postgres and no Redis/Discord calls.

Set SIDETRACK_TEST_API_IMAGE and SIDETRACK_TEST_BOT_IMAGE to locally built tags,
and SIDETRACK_TEST_PREVIOUS_API_IMAGE to a saved Phase 1 image for rollback.
All containers/network created here are removed in finally; the DB fixture is throwaway.
"""

import json
import os
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import docker
import httpx
import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from sidetrack.queue_models import BackgroundJob

API_IMAGE = os.getenv("SIDETRACK_TEST_API_IMAGE")
BOT_IMAGE = os.getenv("SIDETRACK_TEST_BOT_IMAGE")
PREVIOUS_IMAGE = os.getenv("SIDETRACK_TEST_PREVIOUS_API_IMAGE")
pytestmark = pytest.mark.skipif(
    not API_IMAGE or not BOT_IMAGE or not PREVIOUS_IMAGE, reason="Built-image opt-in rehearsal"
)

BOT_SCRIPT = """
const { SidetrackApiClient } = require('./packages/api-client/dist');
const { NotificationDelivery } = require('./apps/bot/dist/notificationDelivery');
const client = new SidetrackApiClient({baseUrl: process.env.SIDETRACK_API_BASE_URL,
                                      authToken: process.env.SIDETRACK_BOT_API_TOKEN});
let sent = 0;
let done;
const delivered = new Promise(resolve => done = resolve);
const api = {
  claimNotifications: () => client.claimNotifications(),
  failNotification: (...args) => client.failNotification(...args),
  acknowledgeNotification: async (...args) => {
    await client.acknowledgeNotification(...args); done();
  }
};
const logger = {info(){}, warn(){}, error(){}, debug(){}};
const pump = new NotificationDelivery(api, async () => {sent++; return '456';}, logger);
const deadline = setTimeout(() => {console.error('Delivery timed out'); process.exit(1);}, 10000);
pump.start();
delivered.then(async () => {
  await pump.stop(); clearTimeout(deadline); console.log(JSON.stringify({sent}));
});
"""


def test_images_enqueue_deliver_restart_and_sigterm(engine, database_url):
    client = docker.from_env()
    suffix = uuid4().hex[:12]
    network = client.networks.create(
        f"sidetrack-phase2-test-{suffix}", labels={"sidetrack.test": "phase2"}
    )
    containers = []
    url = (
        make_url(database_url)
        .set(host="host.docker.internal")
        .render_as_string(hide_password=False)
    )
    environment = {
        "DATABASE_URL": url,
        "SIDETRACK_ENV": "production",
        "SIDETRACK_WEB_API_TOKEN": "test-web-token",
        "SIDETRACK_BOT_API_TOKEN": "test-bot-token",
        # Read only by the pre-Phase-3 image used in the rollback step.
        "SIDETRACK_API_TOKEN": "test-api-token",
        "SIDETRACK_LINK_SECRET": "test-link-secret",
    }
    bot_auth = {"Authorization": "Bearer test-bot-token"}

    def start(image, command=None, **kwargs):
        container = client.containers.run(
            image,
            command=command,
            environment=kwargs.pop("environment", environment),
            network=network.name,
            extra_hosts={"host.docker.internal": "host-gateway"},
            labels={"sidetrack.test": "phase2"},
            detach=True,
            **kwargs,
        )
        containers.append(container)
        return container

    def ready(http):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                if http.get("/health").status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        raise AssertionError("Image API did not become healthy")

    try:
        api = start(
            API_IMAGE, name=f"sidetrack-phase2-api-{suffix}", ports={"8000/tcp": ("127.0.0.1", 0)}
        )
        for _ in range(30):
            api.reload()
            bindings = api.attrs["NetworkSettings"]["Ports"].get("8000/tcp")
            if bindings:
                break
            assert api.status != "exited", api.logs().decode()
            time.sleep(0.1)
        assert bindings, api.logs().decode()
        port = bindings[0]["HostPort"]
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": "Bearer test-web-token"},
            timeout=5,
        ) as http:
            ready(http)
            user = http.post("/users/", json={"display_name": "Image rehearsal"})
            assert user.status_code == 201, user.text
            user_id = user.json()["id"]
            from sqlalchemy import text

            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO club_members (user_id, role, joined_at) "
                        "VALUES (:id, 'admin', clock_timestamp())"
                    ),
                    {"id": user_id},
                )
            http.headers["X-Sidetrack-Act-As"] = f"user:{user_id}"
            accepted = http.post(f"/users/{user_id}/taste-profiles/recompute")
            assert accepted.status_code == 202
            job_id = accepted.json()["job_id"]
            week = http.post(
                "/weeks/",
                json={
                    "label": f"Image rehearsal {suffix}",
                    "nominations_thread_id": "123",
                    "nominations_close_at": (datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
                },
            )
            assert week.status_code == 201, week.text
            worker = start(API_IMAGE, ["python", "-m", "sidetrack.worker", "--once"])
            assert worker.wait(timeout=30)["StatusCode"] == 0, worker.logs().decode()
            assert http.get(f"/jobs/{job_id}/status").json()["status"] == "finished"
            # Recreating API process does not lose accepted work/results.
            api.restart(timeout=5)
            api.reload()
            port = api.attrs["NetworkSettings"]["Ports"]["8000/tcp"][0]["HostPort"]
            http.base_url = f"http://127.0.0.1:{port}"
            ready(http)
            assert http.get(f"/jobs/{job_id}/status").json()["result"]["user_id"] == user_id
            for _ in range(2):
                bot = start(
                    BOT_IMAGE,
                    ["node", "-e", BOT_SCRIPT],
                    environment={
                        "SIDETRACK_API_BASE_URL": f"http://{api.name}:8000",
                        "SIDETRACK_BOT_API_TOKEN": "test-bot-token",
                    },
                )
                assert bot.wait(timeout=20)["StatusCode"] == 0, bot.logs().decode()
                assert json.loads(bot.logs().decode())["sent"] == 1
            claim = http.post(
                "/club/notifications/claim", headers={**bot_auth, "X-Sidetrack-Act-As": ""}
            )
            assert claim.json() == []

            # Linux SIGTERM stops claiming but lets the current domain transaction finish.
            second = http.post(f"/users/{user_id}/taste-profiles/recompute").json()["job_id"]
            with engine.connect() as barrier:
                transaction = barrier.begin()
                barrier.execute(text("LOCK TABLE taste_profiles IN ACCESS EXCLUSIVE MODE"))
                worker = start(API_IMAGE, ["python", "-m", "sidetrack.worker", "--once"])
                try:
                    deadline = time.monotonic() + 15
                    while time.monotonic() < deadline:
                        with Session(engine) as db:
                            if db.get(BackgroundJob, UUID(second)).status == "started":
                                break
                        time.sleep(0.05)
                    else:
                        raise AssertionError("Image worker did not claim work")
                    worker.kill(signal="SIGTERM")
                finally:
                    transaction.rollback()
                assert worker.wait(timeout=20)["StatusCode"] == 0, worker.logs().decode()
            assert http.get(f"/jobs/{second}/status").json()["status"] == "finished"

            # Drain before rollback, retain additive schema and all new job results.
            # The old image must bypass its old Alembic entrypoint, which cannot
            # resolve a newer revision even when the application schema is compatible.
            api.stop(timeout=5)
            previous = start(
                PREVIOUS_IMAGE,
                [
                    "uvicorn",
                    "sidetrack.api.main:create_app",
                    "--factory",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "8000",
                ],
                ports={"8000/tcp": ("127.0.0.1", 0)},
            )
            previous.reload()
            previous_port = previous.attrs["NetworkSettings"]["Ports"]["8000/tcp"][0]["HostPort"]
            with httpx.Client(
                base_url=f"http://127.0.0.1:{previous_port}",
                headers={"Authorization": "Bearer test-api-token"},
                timeout=5,
            ) as old_http:
                ready(old_http)
                assert old_http.get(f"/users/{user_id}").status_code == 200
                assert old_http.get(f"/weeks/{week.json()['id']}").status_code == 200
                with Session(engine) as db:
                    assert db.get(BackgroundJob, UUID(job_id)).status == "finished"
                    assert db.get(BackgroundJob, UUID(second)).status == "finished"
            previous.stop(timeout=5)
            api.start()
            api.reload()
            port = api.attrs["NetworkSettings"]["Ports"]["8000/tcp"][0]["HostPort"]
            http.base_url = f"http://127.0.0.1:{port}"
            ready(http)
            assert http.get(f"/jobs/{job_id}/status").json()["status"] == "finished"
    finally:
        for container in reversed(containers):
            try:
                container.stop(timeout=2)
            finally:
                container.remove(force=True)
        network.remove()
        client.close()
