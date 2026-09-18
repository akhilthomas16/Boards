"""Staff moderation of topics, and @mention notifications."""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from boards.models import Board, Post, Reaction, Topic
from notifications.models import Notification

pytestmark = pytest.mark.django_db(transaction=True)  # see conftest.py


@pytest.fixture
def topic(member):
    """A board with one topic started by alice; returns (alice's client, topic_id)."""
    alice = member("alice")
    board = Board.objects.create(name="General", description="d")
    r = alice.post(f"/api/topics/board/{board.id}", json={"subject": "Hello", "message": "first"})
    assert r.status_code == 201, r.text
    return alice, r.json()["id"]


def test_only_staff_can_pin_or_lock(topic, staff):
    alice, topic_id = topic
    assert alice.patch(f"/api/topics/{topic_id}", json={"is_pinned": True}).status_code == 403
    assert TestClient(app).patch(f"/api/topics/{topic_id}", json={"is_pinned": True}).status_code == 401

    moderated = staff().patch(f"/api/topics/{topic_id}", json={"is_pinned": True, "is_locked": True})
    assert moderated.status_code == 200
    assert moderated.json()["is_pinned"] is True and moderated.json()["is_locked"] is True
    assert alice.post(f"/api/posts/topic/{topic_id}", json={"message": "hi"}).status_code == 403  # locked


def test_moderation_leaves_the_topic_where_it_was_in_the_list(topic, staff):
    """Pinning must not look like new activity — .update(), not .save()."""
    alice, topic_id = topic
    before = Topic.objects.get(pk=topic_id).last_updated
    staff().patch(f"/api/topics/{topic_id}", json={"is_pinned": True})
    assert Topic.objects.get(pk=topic_id).last_updated == before


def test_partial_update_leaves_other_flags_alone(topic, staff):
    _, topic_id = topic
    mod = staff()
    mod.patch(f"/api/topics/{topic_id}", json={"is_locked": True})
    body = mod.patch(f"/api/topics/{topic_id}", json={"is_pinned": True}).json()
    assert body["is_locked"] is True and body["is_pinned"] is True


def test_only_staff_can_delete_a_topic_and_it_takes_the_posts(topic, staff, member):
    alice, topic_id = topic
    bob = member("bob")
    post_id = alice.get(f"/api/posts/topic/{topic_id}").json()["results"][0]["id"]
    bob.post(f"/api/posts/{post_id}/react", json={"emoji": "👍"})

    assert alice.delete(f"/api/topics/{topic_id}").status_code == 403
    assert staff().delete(f"/api/topics/{topic_id}").status_code == 204
    assert not Topic.objects.filter(pk=topic_id).exists()
    assert not Post.objects.filter(topic_id=topic_id).exists()  # PROTECT would have blocked this
    assert not Reaction.objects.filter(post_id=post_id).exists()
    assert alice.get(f"/api/topics/{topic_id}").status_code == 404


def test_post_edit_and_delete_are_author_or_staff(topic, member, staff):
    alice, topic_id = topic
    bob = member("bob")
    post_id = alice.post(f"/api/posts/topic/{topic_id}", json={"message": "mine"}).json()["id"]

    assert bob.patch(f"/api/posts/{post_id}", json={"message": "theirs"}).status_code == 403
    assert bob.delete(f"/api/posts/{post_id}").status_code == 403
    edited = alice.patch(f"/api/posts/{post_id}", json={"message": "edited"})
    assert edited.status_code == 200 and edited.json()["message"] == "edited"
    assert staff().delete(f"/api/posts/{post_id}").status_code == 204


# --- mentions -------------------------------------------------------------------------

def mentions_of(username):
    return list(Notification.objects.filter(recipient__username=username, message="mentioned you")
                .values_list("link", flat=True))


def test_a_mention_in_a_reply_notifies_that_user(topic, member):
    alice, topic_id = topic
    member("bob")
    carol = member("carol")
    post = carol.post(f"/api/posts/topic/{topic_id}", json={"message": "hey @bob and @nobody, look"})
    assert post.status_code == 201
    assert mentions_of("bob") == [f"/topics/{topic_id}#post-{post.json()['id']}"]
    assert mentions_of("nobody") == []


def test_mentions_skip_yourself_and_the_topic_starter(topic, member):
    alice, topic_id = topic  # started by alice
    bob = member("bob")
    bob.post(f"/api/posts/topic/{topic_id}", json={"message": "@bob @alice hello"})
    assert mentions_of("bob") == []
    assert mentions_of("alice") == []  # already got the "replied to your topic" notification
    assert Notification.objects.filter(recipient__username="alice").count() == 1


def test_a_mention_in_a_new_topic_notifies(member):
    alice = member("alice")
    member("bob")
    board = Board.objects.create(name="General", description="d")
    r = alice.post(f"/api/topics/board/{board.id}", json={"subject": "Hi", "message": "ping @bob."})
    assert r.status_code == 201
    assert mentions_of("bob") == [f"/topics/{r.json()['id']}#post-{Post.objects.get(topic_id=r.json()['id']).id}"]


def test_editing_a_post_notifies_newly_mentioned_users(topic, member):
    alice, topic_id = topic
    member("bob")
    post_id = alice.post(f"/api/posts/topic/{topic_id}", json={"message": "nothing yet"}).json()["id"]
    assert mentions_of("bob") == []
    alice.patch(f"/api/posts/{post_id}", json={"message": "now with @bob"})
    assert len(mentions_of("bob")) == 1
