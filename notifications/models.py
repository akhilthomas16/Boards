from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import redis
import json

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+')
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"To {self.recipient.username}: {self.message}"


@receiver(post_save, sender=Notification)
def notify_websocket(sender, instance, created, **kwargs):
    """Publish the new notification to a Redis Pub/Sub channel for FastAPI to consume."""
    if created:
        try:
            r = redis.from_url(settings.CACHES['default']['LOCATION'])
            payload = {
                "id": instance.id,
                "message": instance.message,
                "link": instance.link,
                "actor": instance.actor.username,
                "created_at": instance.created_at.isoformat(),
                "is_read": instance.is_read
            }
            channel_name = f"user_{instance.recipient.id}_notifications"
            r.publish(channel_name, json.dumps(payload))
        except Exception as e:
            # Silently fail if Redis is unreachable to not break DB transaction
            print(f"Failed to publish notification to Redis: {e}")
