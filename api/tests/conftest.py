"""Shared API test setup.

API tests use django_db(transaction=True): TestClient runs sync endpoints in worker threads with their
own DB connections, which can't see rows inside a test-wrapping transaction.
"""
import pytest
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
    """member("bob") → a TestClient logged in as a freshly created user bob."""
    def make(username):
        c = TestClient(app)
        assert c.post("/api/auth/signup", json={"username": username, "email": f"{username}@example.com",
                                                "password": PASSWORD}).status_code == 201
        assert c.post("/api/auth/token", data={"username": username, "password": PASSWORD}).status_code == 200
        return c
    return make
