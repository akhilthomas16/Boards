"""Image uploads, avatars and /media serving. Needs Postgres with CREATEDB on the role."""
import io
import os

import pytest
from PIL import Image

from api.main import media_dir

pytestmark = pytest.mark.django_db(transaction=True)  # see conftest.py


def png_bytes(size=(4, 4)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "red").save(buffer, "PNG")
    return buffer.getvalue()


def upload(client, filename, content, content_type, url="/api/upload/image"):
    return client.post(url, files={"file": (filename, content, content_type)})


@pytest.fixture
def uploads():
    """Delete whatever the test uploaded into media/."""
    created = []
    yield created
    for url in created:
        path = os.path.join(media_dir, url.removeprefix("/media/"))
        if os.path.exists(path):
            os.remove(path)


def test_upload_requires_login(client):
    assert upload(client, "a.png", png_bytes(), "image/png").status_code == 401


def test_html_with_spoofed_image_type_is_rejected(member):
    alice = member("alice")
    r = upload(alice, "evil.html", b"<script>alert(1)</script>", "image/png")
    assert r.status_code == 400


def test_real_image_is_stored_by_detected_format_not_client_name(member, uploads):
    alice = member("alice")
    r = upload(alice, "evil.html", png_bytes(), "text/html")
    assert r.status_code == 200
    url = r.json()["url"]
    uploads.append(url)
    assert url.startswith("/media/uploads/") and url.endswith(".png")

    served = alice.get(url)
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/png"
    assert served.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in served.headers["content-security-policy"]


def test_upload_size_limit(member):
    alice = member("alice")
    too_big = png_bytes() + b"\0" * (5 * 1024 * 1024)
    assert upload(alice, "big.png", too_big, "image/png").status_code == 400


def test_non_image_already_in_media_is_served_as_download(client):
    path = os.path.join(media_dir, "uploads", "legacy-test.html")
    with open(path, "w") as f:
        f.write("<script>alert(1)</script>")
    try:
        r = client.get("/media/uploads/legacy-test.html")
        assert r.headers["content-type"] == "application/octet-stream"
    finally:
        os.remove(path)


def test_avatar_is_validated_and_renamed(member, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    alice = member("alice")
    url = "/api/profiles/me/avatar"
    assert upload(alice, "x.png", b"GIF89a not really", "image/png", url).status_code == 400

    r = upload(alice, "my photo.html", png_bytes(), "image/png", url)
    assert r.status_code == 200
    avatar = r.json()["avatar_url"]
    assert avatar.startswith("/media/avatars/") and avatar.endswith(".png")
    assert "photo" not in avatar and "alice" not in avatar


@pytest.mark.parametrize("website, status", [
    ("https://example.com", 200), ("", 200),
    ("javascript:alert(1)", 400), ("data:text/html,<script>", 400), ("example.com", 400),
])
def test_profile_website_must_be_http(member, website, status):
    alice = member("alice")
    assert alice.patch("/api/profiles/me", json={"website": website}).status_code == status
