"""Auth endpoints over HTTP. Needs Postgres with CREATEDB on the role."""
from unittest import mock

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from fastapi.testclient import TestClient
from jose import jwt
from starlette.websockets import WebSocketDisconnect

from api.limiter import limiter
from api.main import app

GOOD_PASSWORD = "plum-Harbor-42"
NEW_PASSWORD = "new-Harbor-77"
FORGOT_MESSAGE = "If an account with that email exists, a reset code has been sent."

# transaction=True: TestClient runs sync endpoints in worker threads with their own DB connections,
# which can't see rows inside a test-wrapping transaction.
pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def _isolate(settings):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    settings.DEBUG = True
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


def me(client):
    return client.get("/api/auth/me")


def logged_in(username="alice"):
    """A separate browser: its own cookie jar."""
    c = TestClient(app)
    assert login(c, username).status_code == 200
    return c


def refresh_cookie(client):
    return client.cookies.get("refresh_token", path="/api/auth")


def refresh_with(client, token):
    return TestClient(app, cookies={"refresh_token": token}).post("/api/auth/refresh")


# --- signup -------------------------------------------------------------------

def test_signup_creates_user_with_lowercased_email(client):
    r = signup(client, email="Alice@Example.com")
    assert r.status_code == 201
    assert r.json()["email"] == "alice@example.com"


def test_signup_rejects_duplicate_username(client):
    signup(client)
    r = signup(client, email="other@example.com")
    assert r.status_code == 400
    assert r.json()["detail"] == "Username already taken"


def test_signup_rejects_duplicate_email_in_any_case(client):
    signup(client)
    r = signup(client, username="bob", email="ALICE@example.com")
    assert r.status_code == 400
    assert r.json()["detail"] == "Email already registered"


def test_signup_rejects_invalid_email(client):
    assert signup(client, email="not-an-email").status_code == 422


@pytest.mark.parametrize("password", ["a", "password123", "83920174", "alice-example"])
def test_signup_runs_password_validators(client, password):
    assert signup(client, password=password).status_code == 400
    assert not User.objects.filter(username="alice").exists()


# --- login, cookies, refresh ------------------------------------------------------

def test_login_sets_httponly_cookies_and_returns_no_tokens(client):
    signup(client)
    r = login(client)
    assert r.status_code == 200
    assert set(r.json()) == {"id", "username", "email"}
    cookies = r.headers.get_list("set-cookie")
    access = next(c for c in cookies if c.startswith("access_token="))
    refresh = next(c for c in cookies if c.startswith("refresh_token="))
    for cookie in (access, refresh):
        assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert "Path=/api;" in access and "Path=/api/auth;" in refresh
    assert me(client).json()["username"] == "alice"


def test_cookies_are_secure_outside_debug(client, settings):
    signup(client)
    settings.DEBUG = False
    assert all("Secure" in c for c in login(client).headers.get_list("set-cookie"))


def test_login_rejects_wrong_password(client):
    signup(client)
    assert login(client, password="wrong-password").status_code == 401


def test_me_requires_cookie(client):
    assert me(client).status_code == 401


def test_refresh_token_is_not_an_access_token(client):
    signup(client)
    login(client)
    as_access = TestClient(app, cookies={"access_token": refresh_cookie(client)})
    assert me(as_access).status_code == 401


def test_refresh_rotates_the_pair(client):
    signup(client)
    login(client)
    old = refresh_cookie(client)
    r = client.post("/api/auth/refresh")
    assert r.status_code == 200
    assert refresh_cookie(client) != old
    assert me(client).status_code == 200


def test_refresh_replay_after_grace_revokes_the_family(client):
    signup(client)
    login(client)
    stolen = refresh_cookie(client)
    assert client.post("/api/auth/refresh").status_code == 200  # legitimate rotation
    cache.delete(f"auth:used:{jwt.get_unverified_claims(stolen)['jti']}")  # grace window over

    assert refresh_with(client, stolen).status_code == 401  # replay
    assert me(client).status_code == 401  # the legitimate session's family is revoked too
    assert client.post("/api/auth/refresh").status_code == 401


def test_refresh_replay_inside_grace_does_not_revoke(client):
    signup(client)
    login(client)
    raced = refresh_cookie(client)
    assert client.post("/api/auth/refresh").status_code == 200  # the other tab won
    assert refresh_with(client, raced).status_code == 401
    assert me(client).status_code == 200


def test_logout_revokes_tokens_and_clears_cookies(client):
    signup(client)
    login(client)
    access = client.cookies.get("access_token", path="/api")
    assert client.post("/api/auth/logout").status_code == 204
    assert me(client).status_code == 401
    assert me(TestClient(app, cookies={"access_token": access})).status_code == 401


# --- deactivation (the ban) -----------------------------------------------------------

def test_deactivated_user_is_locked_out_everywhere(client):
    signup(client)
    login(client)
    User.objects.filter(username="alice").update(is_active=False)
    assert me(client).status_code == 401
    assert client.post("/api/auth/refresh").status_code == 401
    assert login(TestClient(app)).status_code == 401


def test_token_resolves_user_by_id_not_username(client):
    signup(client)
    login(client)
    User.objects.filter(username="alice").update(username="alice2")
    assert me(client).json()["username"] == "alice2"


# --- password changes -----------------------------------------------------------------

def test_change_password_logs_out_other_sessions(client):
    signup(client)
    login(client)
    other_device = logged_in()
    url = "/api/auth/change-password"

    assert TestClient(app).post(url, json={"old_password": "x", "new_password": NEW_PASSWORD}).status_code == 401
    wrong_old = client.post(url, json={"old_password": "nope", "new_password": NEW_PASSWORD})
    assert wrong_old.json()["detail"] == "Current password is incorrect"
    assert client.post(url, json={"old_password": GOOD_PASSWORD, "new_password": "alice"}).status_code == 400

    assert client.post(url, json={"old_password": GOOD_PASSWORD, "new_password": NEW_PASSWORD}).status_code == 200
    assert me(client).status_code == 200  # this session got fresh cookies
    assert me(other_device).status_code == 401
    assert login(TestClient(app)).status_code == 401
    assert login(TestClient(app), password=NEW_PASSWORD).status_code == 200


# --- forgot / reset password ---------------------------------------------------------------

def request_code(client, email="alice@example.com"):
    with mock.patch("api.tasks.send_otp_email") as send:
        r = client.post("/api/auth/forgot-password", json={"email": email})
    return r, (send.call_args.args[1] if send.called else None)


def reset(client, otp, password=NEW_PASSWORD, email="alice@example.com"):
    return client.post("/api/auth/reset-password", json={"email": email, "otp": otp, "new_password": password})


def test_forgot_password_same_message_for_known_and_unknown_email(client):
    signup(client)
    known, otp = request_code(client, "ALICE@example.com")
    unknown, no_otp = request_code(client, "nobody@example.com")
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json() == {"message": FORGOT_MESSAGE}
    assert otp is not None and len(otp) == 6 and otp.isdigit()
    assert no_otp is None


def test_reset_password_runs_validators_and_logs_out_sessions(client):
    signup(client)
    session = logged_in()
    _, otp = request_code(client)
    assert client.post("/api/auth/verify-otp", json={"email": "alice@example.com", "otp": otp}).status_code == 200
    assert reset(client, otp, password="12345678").status_code == 400
    assert reset(client, otp).status_code == 200
    assert me(session).status_code == 401
    assert login(TestClient(app), password=NEW_PASSWORD).status_code == 200
    assert reset(client, otp, password="another-Harbor-1").status_code == 400  # code consumed


def test_five_wrong_codes_burn_the_code(client):
    signup(client)
    _, otp = request_code(client)
    wrong = "000000" if otp != "000000" else "111111"
    for _ in range(5):
        assert reset(client, wrong).status_code == 400
    assert reset(client, otp).status_code == 400
    assert login(TestClient(app)).status_code == 200  # password unchanged


def test_reset_without_a_code_fails(client):
    signup(client)
    assert reset(client, "123456").status_code == 400


# --- profiles ----------------------------------------------------------------------------

def test_public_profile_and_search_hide_email(client):
    signup(client)
    login(client)
    anonymous = TestClient(app)
    assert "email" not in anonymous.get("/api/profiles/alice").json()
    assert all("email" not in u for u in anonymous.get("/api/profiles/search/users?q=al").json())
    assert anonymous.get("/api/profiles/search/users?q=a").status_code == 422
    assert client.get("/api/profiles/me").json()["email"] == "alice@example.com"


# --- notifications WebSocket ----------------------------------------------------------------

def ws_connect(client, origin=None):
    from django.conf import settings
    headers = {"origin": origin or settings.CORS_ALLOWED_ORIGINS[0]}
    with client.websocket_connect("/api/notifications/ws", headers=headers):
        pass


def test_websocket_accepts_a_logged_in_user(client):
    signup(client)
    login(client)
    ws_connect(client)


@pytest.mark.parametrize("case", ["anonymous", "bad_origin", "deactivated"])
def test_websocket_rejects_before_accept(client, case):
    signup(client)
    login(client)
    if case == "anonymous":
        client = TestClient(app)
    if case == "deactivated":
        User.objects.filter(username="alice").update(is_active=False)
    with pytest.raises(WebSocketDisconnect):
        ws_connect(client, origin="https://evil.example" if case == "bad_origin" else None)
