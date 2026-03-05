"""
Elasticsearch document definitions for Board, Topic, and Post models.
"""
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from .models import Board, Topic, Post


@registry.register_document
class BoardDocument(Document):
    class Index:
        name = 'boards'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }

    class Django:
        model = Board
        fields = ['name', 'description']


@registry.register_document
class TopicDocument(Document):
    board_name = fields.TextField(attr='board.name')
    starter_username = fields.TextField(attr='starter.username')

    class Index:
        name = 'topics'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }

    class Django:
        model = Topic
        fields = ['subject', 'views_count', 'last_updated']


@registry.register_document
class PostDocument(Document):
    topic_subject = fields.TextField(attr='topic.subject')
    board_name = fields.TextField(attr='topic.board.name')
    author_username = fields.TextField(attr='created_by.username')

    class Index:
        name = 'posts'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }

    class Django:
        model = Post
        fields = ['message', 'created_at']
