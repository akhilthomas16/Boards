from django.db import models
from django.contrib.auth.models import User


# Create your models here.

class Board(models.Model):
    name = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Topic(models.Model):
    subject = models.CharField(max_length=255)
    last_updated = models.DateTimeField(auto_now=True)
    board = models.ForeignKey(Board, on_delete=models.PROTECT, related_name='topics')
    starter = models.ForeignKey(User, on_delete=models.PROTECT, related_name='topics')


class Post(models.Model):
    message = models.TextField(max_length=4000)
    topic = models.ForeignKey(Topic, on_delete=models.PROTECT, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='posts')
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name='+')


# class User(models.Model):
#     username = models.CharField(max_length=30, unique=True)
#     password = models.CharField(max_length=16, )
#     email = models.EmailField(max_length=50, unique=True)
#     is_superuser = models.BooleanField()
