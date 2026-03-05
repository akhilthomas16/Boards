"""
Celery tasks for background processing — search indexing, LLM, notifications.
"""
from celery import shared_task


@shared_task(name="index_post_to_elasticsearch")
def index_post_to_elasticsearch(post_id: int):
    """Index a new/updated post in Elasticsearch."""
    try:
        from boards.models import Post
        from boards.documents import PostDocument

        post = Post.objects.get(pk=post_id)
        PostDocument().update(post)
    except Exception as e:
        print(f"Failed to index post {post_id}: {e}")


@shared_task(name="index_topic_to_elasticsearch")
def index_topic_to_elasticsearch(topic_id: int):
    """Index a new/updated topic in Elasticsearch."""
    try:
        from boards.models import Topic
        from boards.documents import TopicDocument

        topic = Topic.objects.get(pk=topic_id)
        TopicDocument().update(topic)
    except Exception as e:
        print(f"Failed to index topic {topic_id}: {e}")


@shared_task(name="generate_content_task")
def generate_content_task(prompt: str, context: str = ""):
    """Background LLM content generation task."""
    try:
        import openai
        from django.conf import settings

        client = openai.OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

        messages = [
            {"role": "system", "content": "You are a helpful forum assistant."},
        ]
        if context:
            messages.append({"role": "user", "content": f"Context: {context}"})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )

        return {
            "generated_text": response.choices[0].message.content,
            "model": settings.OPENAI_MODEL,
            "tokens_used": response.usage.total_tokens if response.usage else None,
        }
    except Exception as e:
        return {"error": str(e)}


@shared_task(name="send_notification_email")
def send_notification_email(user_id: int, subject: str, message: str):
    """Send email notification to a user."""
    try:
        from django.contrib.auth.models import User
        from django.core.mail import send_mail

        user = User.objects.get(pk=user_id)
        send_mail(
            subject=subject,
            message=message,
            from_email=None,  # uses DEFAULT_FROM_EMAIL
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Failed to send email to user {user_id}: {e}")


@shared_task(name="send_otp_email")
def send_otp_email(email: str, otp: str):
    """Send password reset OTP to user's email."""
    from django.core.mail import send_mail

    send_mail(
        subject="Your password reset code",
        message=f"Your password reset code is: {otp}\n\nThis code expires in 10 minutes.",
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )


@shared_task(name="rebuild_search_index")
def rebuild_search_index():
    """Rebuild all Elasticsearch indices."""
    try:
        from django.core.management import call_command
        call_command('search_index', '--rebuild', '-f')
    except Exception as e:
        print(f"Failed to rebuild search index: {e}")
