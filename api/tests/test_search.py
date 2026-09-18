"""Search over the ORM. Needs Postgres with CREATEDB on the role."""
import pytest
from django.contrib.auth.models import User

from boards.models import Board, Post, Topic

pytestmark = pytest.mark.django_db(transaction=True)  # see conftest.py

TERM = "gamma"


@pytest.fixture
def corpus():
    """1 board, 2 topics and 3 posts matching TERM (plus non-matching noise)."""
    user = User.objects.create_user("alice", "alice@example.com", "x")
    board = Board.objects.create(name=f"{TERM} board", description="d")
    other = Board.objects.create(name="quiet", description="nothing here")
    topics = [Topic.objects.create(subject=f"{TERM} topic {i}", board=board, starter=user) for i in range(2)]
    Topic.objects.create(subject="unrelated", board=other, starter=user)
    posts = [Post.objects.create(message=f"about {TERM} number {i}", topic=topics[0], created_by=user)
             for i in range(3)]
    Post.objects.create(message="unrelated", topic=topics[0], created_by=user)
    return {"board": board, "topics": topics, "posts": posts}


def search(client, **params):
    query = "&".join(f"{k}={v}" for k, v in {"q": TERM, **params}.items())
    r = client.get(f"/api/search/?{query}")
    assert r.status_code == 200, r.text
    return r.json()


def test_counts_and_total_match_what_exists(client, corpus):
    body = search(client)
    assert body["counts"] == {"board": 1, "topic": 2, "post": 3}
    assert body["total"] == 6 == len(body["results"])


def test_pages_cover_every_match_exactly_once(client, corpus):
    seen = []
    for page in (1, 2, 3):
        body = search(client, page=page, page_size=2)
        assert body["total"] == 6
        seen += [(r["type"], r["id"]) for r in body["results"]]
    assert len(seen) == len(set(seen)) == 6
    assert [t for t, _ in seen] == ["board", "topic", "topic", "post", "post", "post"]
    assert search(client, page=4, page_size=2)["results"] == []


def test_post_hits_link_to_their_topic(client, corpus):
    body = search(client, type="post")
    assert body["counts"] == {"post": 3}
    assert body["total"] == 3
    topic_id = corpus["topics"][0].id
    for result, post in zip(body["results"], corpus["posts"], strict=True):
        assert result["id"] == post.id
        assert result["url"] == f"/topics/{topic_id}"
        assert result["title"] == corpus["topics"][0].subject


def test_type_filter_and_validation(client, corpus):
    assert search(client, type="board")["counts"] == {"board": 1}
    assert client.get("/api/search/?q=g").status_code == 422
    assert client.get(f"/api/search/?q={TERM}&type=user").status_code == 422
