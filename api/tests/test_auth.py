"""Auth endpoints over HTTP. Needs Postgres with CREATEDB on the role."""
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.limiter import limiter
from api.main import app

GOOD_PASSWORD = "plum-Harbor-42"
FORGOT_MESSAGE = "If an account with that email exists, a reset code has been sent."

# transaction=True: TestClient runs sync endpoints in worker threads with their own DB connections,
# which can't see rows inside a test-wrapping transaction.
pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def _isolate(settings):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture
def client():
    return TestClient(app)


def signup(client, username="alice", email="alice@example.com", password=GOOD_PASSWORD):
    return client.post("/api/auth/signup", json={"username": username, "email": email, "password": password})


def login(client, username="alice", password=GOOD_PASSWORD):
    return client.post("/api/auth/token", data={"username": username, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_signup_creates_user(client):
    r = signup(client)
    assert r.status_code == 201
    assert r.json()["username"] == "alice"
    assert r.json()["email"] == "alice@example.com"


def test_signup_rejects_duplicate_username(client):
    signup(client)
    r = signup(client, email="other@example.com")
    assert r.status_code == 400
    assert r.json()["detail"] == "Username already taken"


def test_signup_rejects_duplicate_email(client):
    signup(client)
    r = signup(client, username="bob")
    assert r.status_code == 400
    assert r.json()["detail"] == "Email already registered"


@pytest.mark.parametrize("password", ["a", "password123", "83920174", "alice-example"])
def test_signup_runs_password_validators(client, password):
    r = signup(client, password=password)
    assert r.status_code == 400
    assert not client.post("/api/auth/token", data={"username": "alice", "password": password}).is_success


def test_login_returns_access_and_refresh_pair(client):
    signup(client)
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"access_token", "refresh_token", "token_type"}
    assert body["token_type"] == "bearer"
    assert client.get("/api/auth/me", headers=bearer(body["access_token"])).json()["username"] == "alice"


def test_login_rejects_wrong_password(client):
    signup(client)
    assert login(client, password="wrong-password").status_code == 401


def test_refresh_accepts_refresh_token_and_rejects_access_token(client):
    signup(client)
    tokens = login(client).json()
    assert client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 200
    r = client.post("/api/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid token type"


def test_forgot_password_same_message_for_known_and_unknown_email(client):
    signup(client)
    with mock.patch("api.tasks.send_otp_email") as send:
        known = client.post("/api/auth/forgot-password", json={"email": "alice@example.com"})
        unknown = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json() == {"message": FORGOT_MESSAGE}
    send.delay.assert_called_once()


def test_reset_password_runs_validators(client):
    from django.core.cache import cache

    signup(client)
    cache.set("otp:alice@example.com", "123456", timeout=600)
    body = {"email": "alice@example.com", "otp": "123456"}
    assert client.post("/api/auth/reset-password", json={**body, "new_password": "12345678"}).status_code == 400
    assert client.post("/api/auth/reset-password", json={**body, "new_password": "new-Harbor-77"}).status_code == 200
    assert login(client, password="new-Harbor-77").status_code == 200


def test_change_password(client):
    signup(client)
    headers = bearer(login(client).json()["access_token"])
    url = "/api/auth/change-password"

    assert client.post(url, json={"old_password": "x", "new_password": "new-Harbor-77"}).status_code == 401
    wrong_old = client.post(url, headers=headers, json={"old_password": "nope", "new_password": "new-Harbor-77"})
    assert wrong_old.json()["detail"] == "Current password is incorrect"
    assert client.post(url, headers=headers, json={"old_password": GOOD_PASSWORD, "new_password": "alice"}).status_code == 400

    r = client.post(url, headers=headers, json={"old_password": GOOD_PASSWORD, "new_password": "new-Harbor-77"})
    assert r.status_code == 200
    assert login(client).status_code == 401
    assert login(client, password="new-Harbor-77").status_code == 200


def test_me_rejects_refresh_token(client):
    signup(client)
    refresh = login(client).json()["refresh_token"]
    assert client.get("/api/auth/me", headers=bearer(refresh)).status_code == 401
    assert client.get("/api/auth/me", headers=bearer(create_access_token({"sub": "ghost"}))).status_code == 401
