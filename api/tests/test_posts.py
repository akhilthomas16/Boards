"""Topics, posts and reactions over HTTP. Needs Postgres with CREATEDB on the role."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from accounts.models import UserProfile
from api.main import app
from boards.models import Board, Topic

pytestmark = pytest.mark.django_db(transaction=True)  # see conftest.py


@pytest.fixture
def topic_by(member):
    """Create a board and a topic started by `username`; returns (client, topic_id, first_post_id)."""
    def make(username):
        c = member(username)
        board = Board.objects.create(name="General", description="d")
        r = c.post(f"/api/topics/board/{board.id}", json={"subject": "Hello", "message": "first"})
        assert r.status_code == 201, r.text
        topic_id = r.json()["id"]
        post_id = c.get(f"/api/posts/topic/{topic_id}").json()["results"][0]["id"]
        return c, topic_id, post_id
    return make


def reputation(username):
    return UserProfile.objects.get(user__username=username).reputation_score


def react(client, post_id, emoji="👍"):
    return client.post(f"/api/posts/{post_id}/react", json={"emoji": emoji})


def test_reaction_from_someone_else_grants_and_revokes_reputation(topic_by, member):
    _, _, post_id = topic_by("alice")
    bob = member("bob")
    assert react(bob, post_id).json()["action"] == "added"
    assert reputation("alice") == 1
    assert react(bob, post_id).json()["action"] == "removed"
    assert reputation("alice") == 0
    react(bob, post_id)
    UserProfile.objects.filter(user__username="alice").update(reputation_score=0)
    react(bob, post_id)  # removal never goes below zero
    assert reputation("alice") == 0


def test_reacting_to_your_own_post_grants_nothing(topic_by):
    alice, _, post_id = topic_by("alice")
    react(alice, post_id, "👍")
    react(alice, post_id, "❤️")
    assert reputation("alice") == 0


def test_unknown_emoji_is_rejected(topic_by, member):
    _, _, post_id = topic_by("alice")
    assert react(member("bob"), post_id, "<img src=x>").status_code == 422


def test_concurrent_views_are_all_counted(topic_by):
    _, topic_id, _ = topic_by("alice")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: TestClient(app).get(f"/api/topics/{topic_id}"), range(40)))
    assert Topic.objects.get(pk=topic_id).views_count == 40


def test_reply_moves_topic_to_the_top_of_the_board(topic_by, member):
    alice, older_id, _ = topic_by("alice")
    board_id = Topic.objects.get(pk=older_id).board_id
    newer_id = alice.post(f"/api/topics/board/{board_id}", json={"subject": "Newer", "message": "m"}).json()["id"]
    def listed():
        return [t["id"] for t in alice.get(f"/api/topics/board/{board_id}").json()["results"]]
    assert listed() == [newer_id, older_id]

    assert member("bob").post(f"/api/posts/topic/{older_id}", json={"message": "reply"}).status_code == 201
    assert listed() == [older_id, newer_id]


def test_my_reactions_are_reported_for_the_viewer_only(topic_by, member):
    alice, topic_id, post_id = topic_by("alice")
    bob = member("bob")
    react(bob, post_id, "👍")
    react(alice, post_id, "❤️")

    def first_post(client):
        return client.get(f"/api/posts/topic/{topic_id}").json()["results"][0]

    assert first_post(bob)["my_reactions"] == ["👍"]
    assert first_post(alice)["my_reactions"] == ["❤️"]
    assert first_post(TestClient(app))["my_reactions"] == []  # anonymous
    assert first_post(bob)["reactions"] == {"👍": 1, "❤️": 1}


def test_my_reactions_endpoint_is_per_user(topic_by, member):
    """The topic page is server-rendered without a cookie, so the browser asks for this separately."""
    alice, topic_id, post_id = topic_by("alice")
    bob = member("bob")
    react(bob, post_id, "👍")
    react(alice, post_id, "❤️")

    assert bob.get(f"/api/posts/topic/{topic_id}/my-reactions").json() == {str(post_id): ["👍"]}
    assert alice.get(f"/api/posts/topic/{topic_id}/my-reactions").json() == {str(post_id): ["❤️"]}
    assert TestClient(app).get(f"/api/posts/topic/{topic_id}/my-reactions").status_code == 401
