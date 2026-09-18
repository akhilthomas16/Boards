"""Model-level behaviour. Needs Postgres with CREATEDB on the role."""
import pytest
from django.contrib.auth.models import User
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from boards.models import Board, Post, Topic

pytestmark = pytest.mark.django_db(transaction=True)


def migrate(targets):
    executor = MigrationExecutor(connection)
    executor.migrate(targets)
    executor.loader.build_graph()
    return executor.loader.project_state(targets).apps


def test_migration_0003_backfills_unique_slugs_on_existing_boards():
    old_apps = migrate([("boards", "0002_remove_topic_last_update_topic_last_updated")])
    OldBoard = old_apps.get_model("boards", "Board")
    for name in ["General", "Off Topic", "off-topic", "!!!"]:
        OldBoard.objects.create(name=name, description="d")
    try:
        new_apps = migrate([("boards", "0003_alter_board_options_alter_post_options_and_more")])
        slugs = list(new_apps.get_model("boards", "Board").objects.order_by("pk").values_list("slug", flat=True))
        pks = list(new_apps.get_model("boards", "Board").objects.order_by("pk").values_list("pk", flat=True))
        assert slugs == ["general", "off-topic", f"off-topic-{pks[2]}", f"board-{pks[3]}"]
    finally:
        migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())


def test_reply_bumps_topic_to_the_top():
    user = User.objects.create_user("alice", "alice@example.com", "x")
    board = Board.objects.create(name="General", description="d")
    older = Topic.objects.create(subject="older", board=board, starter=user)
    Post.objects.create(message="first", topic=older, created_by=user)
    newer = Topic.objects.create(subject="newer", board=board, starter=user)
    Post.objects.create(message="first", topic=newer, created_by=user)
    assert list(Topic.objects.values_list("subject", flat=True)) == ["newer", "older"]

    Post.objects.create(message="reply", topic=older, created_by=user)
    assert list(Topic.objects.values_list("subject", flat=True)) == ["older", "newer"]
