"""Shared API test setup.

API tests use django_db(transaction=True): TestClient runs sync endpoints in worker threads with their
own DB connections, which can't see rows inside a test-wrapping transaction.
"""
import pytest
from django.contrib.auth.models import User
from fastapi.testclient import TestClient

from api.limiter import limiter
from api.main import app

PASSWORD = "plum-Harbor-42"


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


@pytest.fixture
def member():
    """member("bob") → a TestClient logged in as a verified user bob (signup + verify has its own tests)."""
    def make(username, **fields):
        user = User.objects.create_user(username, f"{username}@example.com", PASSWORD, **fields)
        user.profile.email_verified = True
        user.profile.save(update_fields=["email_verified"])
        c = TestClient(app)
        assert c.post("/api/auth/token", data={"username": username, "password": PASSWORD}).status_code == 200
        return c
    return make


@pytest.fixture
def staff(member):
    """A logged-in moderator."""
    def make(username="mod"):
        return member(username, is_staff=True)
    return make
