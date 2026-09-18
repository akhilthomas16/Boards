"""@username mentions in topic and post bodies."""
import re

from django.contrib.auth.models import User

# Django usernames allow letters, digits and @/./+/-/_ ; trailing punctuation is sentence noise.
MENTION = re.compile(r"(?:^|\s)@([\w][\w.+-]*)")
MAX_MENTIONS = 10


def notify_mentions(message: str, actor: User, link: str, skip_user_ids=()) -> int:
    """Notify everyone named with @username in `message`. Returns how many were notified."""
    names = {name.rstrip(".+-") for name in MENTION.findall(message or "")}
    names.discard("")
    if not names:
        return 0

    from notifications.models import Notification

    recipients = (User.objects.filter(username__in=list(names)[:MAX_MENTIONS], is_active=True)
                  .exclude(pk__in={actor.pk, *skip_user_ids}))
    for recipient in recipients:
        # One at a time, not bulk_create: the post_save signal is what pushes to the WebSocket.
        Notification.objects.create(
            recipient=recipient,
            actor=actor,
            message="mentioned you",
            link=link,
        )
    return len(recipients)
