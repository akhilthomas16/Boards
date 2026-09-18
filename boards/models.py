from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify


class Board(models.Model):
    name = models.CharField(max_length=30, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    description = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Topic(models.Model):
    subject = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    board = models.ForeignKey(Board, on_delete=models.PROTECT, related_name='topics')
    starter = models.ForeignKey(User, on_delete=models.PROTECT, related_name='topics')
    views_count = models.PositiveIntegerField(default=0)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    tags = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-is_pinned', '-last_updated']
        indexes = [
            models.Index(fields=['board', '-is_pinned', '-last_updated']),  # a board's topic list
            models.Index(fields=['-views_count', '-last_updated']),  # trending
        ]

    def __str__(self):
        return self.subject

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.subject)[:280]
        super().save(*args, **kwargs)


class Post(models.Model):
    message = models.TextField(max_length=4000)
    topic = models.ForeignKey(Topic, on_delete=models.PROTECT, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='posts')
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name='+')

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['topic', 'created_at'])]  # a topic's posts, in order

    def __str__(self):
        return f'Post by {self.created_by.username} on {self.topic.subject}'


@receiver(post_save, sender=Post)
def bump_topic_on_reply(sender, instance, created, **kwargs):
    """A new post moves its topic to the top of the default ordering."""
    if created:
        # .update(), not save(): no auto_now side effects, no re-fetch, no race with a concurrent reply.
        Topic.objects.filter(pk=instance.topic_id).update(last_updated=timezone.now())


class Reaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reactions')
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='reactions')
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post', 'emoji')

    def __str__(self):
        return f"{self.user.username} reacted {self.emoji} to post {self.post.id}"
