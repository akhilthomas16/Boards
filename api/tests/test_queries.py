"""List endpoints must cost the same number of queries whatever the row count."""
import pytest
from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext

from api.routers.boards import list_boards
from api.routers.posts import list_posts
from api.routers.topics import list_topics, trending_topics
from boards.models import Board, Post, Reaction, Topic

pytestmark = pytest.mark.django_db


def seed(boards=1, topics=1, posts=1):
    users = [User.objects.get_or_create(username=f"u{i}", defaults={"email": f"u{i}@example.com"})[0]
             for i in range(3)]
    made = []
    for b in range(Board.objects.count(), Board.objects.count() + boards):
        board = Board.objects.create(name=f"board {b}", description="d")
        for t in range(topics):
            topic = Topic.objects.create(subject=f"topic {t}", board=board, starter=users[t % 3])
            for p in range(posts):
                post = Post.objects.create(message=f"post {p}", topic=topic, created_by=users[p % 3])
                Reaction.objects.create(user=users[(p + 1) % 3], post=post, emoji="👍")
            made.append((board, topic))
    return made


def test_board_list_is_flat():
    seed(boards=2, topics=2, posts=2)
    with CaptureQueriesContext(connection) as few:
        list_boards(page=1, page_size=20)
    seed(boards=8, topics=3, posts=3)
    Board.objects.create(name="aardvark", description="d")  # created last, sorts first
    with CaptureQueriesContext(connection) as many:
        list_boards(page=1, page_size=20)
    assert len(few.captured_queries) == len(many.captured_queries) <= 3
    names = [b["name"] for b in list_boards(page=1, page_size=20)["results"]]
    assert names == sorted(names)  # aggregation must not drop Meta.ordering

    for row in list_boards(page=1, page_size=20)["results"]:
        board = Board.objects.get(pk=row["id"])
        assert row["topics_count"] == board.topics.count()  # distinct=True, not a join blow-up
        assert row["posts_count"] == Post.objects.filter(topic__board=board).count()


def test_topic_list_is_flat():
    made = seed(boards=1, topics=5, posts=2)
    board = made[0][0]
    with CaptureQueriesContext(connection) as few:
        list_topics(board_id=board.id, page=1, page_size=50)
    for t in range(45):
        topic = Topic.objects.create(subject=f"extra {t}", board=board, starter=User.objects.first())
        Post.objects.create(message="m", topic=topic, created_by=User.objects.first())
    with CaptureQueriesContext(connection) as many:
        list_topics(board_id=board.id, page=1, page_size=50)
    assert len(many.captured_queries) == len(few.captured_queries) <= 4
    assert Topic.objects.count() == 50
    updated = [t["last_updated"] for t in list_topics(board_id=board.id, page=1, page_size=50)["results"]]
    assert updated == sorted(updated, reverse=True)  # newest first, Meta.ordering survived


def test_post_list_is_flat():
    made = seed(boards=1, topics=1, posts=3)
    topic = made[0][1]
    with CaptureQueriesContext(connection) as few:
        list_posts(topic_id=topic.id, page=1, page_size=50)
    for p in range(20):
        Post.objects.create(message=f"extra {p}", topic=topic, created_by=User.objects.first())
    with CaptureQueriesContext(connection) as many:
        list_posts(topic_id=topic.id, page=1, page_size=50)
    assert len(many.captured_queries) == len(few.captured_queries) <= 5
    created = [p["created_at"] for p in list_posts(topic_id=topic.id, page=1, page_size=50)["results"]]
    assert created == sorted(created)  # oldest first, Meta.ordering survived


def test_trending_is_flat():
    seed(boards=1, topics=2, posts=2)
    with CaptureQueriesContext(connection) as few:
        trending_topics()
    seed(boards=2, topics=10, posts=2)
    with CaptureQueriesContext(connection) as many:
        trending_topics()
    assert len(many.captured_queries) == len(few.captured_queries) <= 2


def test_saving_a_user_does_not_rewrite_their_profile():
    """The old save_user_profile receiver wrote UserProfile on every User.save()."""
    user = User.objects.create_user("writer", "writer@example.com", "x")
    user.set_password("another-Harbor-1")
    with CaptureQueriesContext(connection) as captured:
        user.save()
    assert not [q for q in captured.captured_queries if "accounts_userprofile" in q["sql"]]
