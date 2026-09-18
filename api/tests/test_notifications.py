"""Notification WebSocket delivery and cleanup. Needs Postgres (CREATEDB) and Redis.

Runs a real uvicorn server: Starlette's TestClient cancels the handler when the test closes the socket,
which hides a handler that never notices a disconnect.
"""
import socket
import threading
import time

import pytest
import redis
import uvicorn
from django.conf import settings
from django.contrib.auth.models import User
from websockets.sync.client import connect

from api.main import app
from notifications.models import Notification

pytestmark = pytest.mark.django_db(transaction=True)  # see conftest.py


@pytest.fixture
def server_url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, port=port, log_level="warning", ws="websockets"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    yield f"ws://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


def subscribers(user):
    channel = f"user_{user.id}_notifications"
    return dict(redis.from_url(settings.REDIS_URL).pubsub_numsub(channel))[channel.encode()]


def wait_until(condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return False


def test_notification_is_pushed_and_disconnect_releases_the_subscription(member, server_url):
    alice = member("alice")
    user = User.objects.get(username="alice")
    cookie = f"access_token={alice.cookies.get('access_token', path='/api')}"

    with connect(f"{server_url}/api/notifications/ws", origin=settings.CORS_ALLOWED_ORIGINS[0],
                 additional_headers={"Cookie": cookie}) as ws:
        assert wait_until(lambda: subscribers(user) == 1)
        Notification.objects.create(recipient=user, actor=user, message="ping", link="/")
        assert '"ping"' in ws.recv(timeout=3)

    # The tab closed and nothing else was published: the server must notice on its own.
    assert wait_until(lambda: subscribers(user) == 0), "handler kept its Redis subscription after disconnect"


@pytest.fixture
def noisy(member):
    """A logged-in user with 25 notifications, 25 unread."""
    client = member("alice")
    user = User.objects.get(username="alice")
    for i in range(25):
        Notification.objects.create(recipient=user, actor=user, message=f"ping {i}", link="/")
    return client


def test_pagination_and_unread_count(noisy):
    first = noisy.get("/api/notifications/?page_size=10").json()
    assert first["count"] == 25 and first["total_pages"] == 3 and len(first["results"]) == 10
    assert first["results"][0]["message"] == "ping 24"  # newest first
    assert len(noisy.get("/api/notifications/?page=3&page_size=10").json()["results"]) == 5
    assert noisy.get("/api/notifications/unread-count").json() == {"unread": 25}


def test_mark_one_read_then_all(noisy):
    one = noisy.get("/api/notifications/").json()["results"][0]["id"]
    assert noisy.post(f"/api/notifications/{one}/read").json()["is_read"] is True
    assert noisy.get("/api/notifications/unread-count").json()["unread"] == 24

    assert noisy.post("/api/notifications/read-all").json() == {"unread": 0}
    assert noisy.get("/api/notifications/unread-count").json()["unread"] == 0
    assert Notification.objects.filter(is_read=False).count() == 0


def test_delete_and_ownership(noisy, member):
    mine = noisy.get("/api/notifications/").json()["results"][0]["id"]
    bob = member("bob")
    assert bob.post(f"/api/notifications/{mine}/read").status_code == 404  # not bob's
    assert bob.delete(f"/api/notifications/{mine}").status_code == 404
    assert noisy.delete(f"/api/notifications/{mine}").status_code == 204
    assert not Notification.objects.filter(pk=mine).exists()
    assert noisy.delete(f"/api/notifications/{mine}").status_code == 404
