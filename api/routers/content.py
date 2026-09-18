"""
LLM content generation endpoints — topic summaries, reply suggestions.
"""
from django.conf import settings
from django.contrib.auth.models import User
from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import get_current_user
from ..limiter import limiter
from ..schemas import ContentGenerateRequest, ContentGenerateResponse

router = APIRouter()


def _generate(data: ContentGenerateRequest) -> ContentGenerateResponse:
    """Run one LLM completion. Plain function: no Request, no Depends, no rate limit."""
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="LLM service not configured")

    import openai

    system_prompt = (
        "You are a helpful forum assistant. Generate content that is "
        "informative, well-structured, and appropriate for a discussion board. "
        "Keep responses concise and relevant."
    )
    messages = [{"role": "system", "content": system_prompt}]
    if data.context:
        messages.append({"role": "user", "content": f"Context: {data.context}"})
    messages.append({"role": "user", "content": data.prompt})

    try:
        client = openai.OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )
    except openai.APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM API error: {e}")

    return ContentGenerateResponse(
        generated_text=response.choices[0].message.content,
        model=settings.OPENAI_MODEL,
        tokens_used=response.usage.total_tokens if response.usage else None,
    )


@router.post("/generate", response_model=ContentGenerateResponse)
@limiter.limit("5/minute")
def generate_content(
    request: Request,
    data: ContentGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate content using LLM (synchronous, for short completions)."""
    return _generate(data)


@router.post("/suggest-reply")
@limiter.limit("3/minute")
def suggest_reply(
    request: Request,
    topic_id: int,
    current_user: User = Depends(get_current_user),
):
    """Generate a suggested reply based on topic context."""
    from boards.models import Post, Topic

    try:
        topic = Topic.objects.get(pk=topic_id)
    except Topic.DoesNotExist:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Gather context from existing posts
    posts = Post.objects.filter(topic=topic).order_by('-created_at')[:5]
    context = f"Topic: {topic.subject}\n\n"
    context += "\n".join([f"{p.created_by.username}: {p.message[:200]}" for p in posts])

    return _generate(ContentGenerateRequest(
        prompt="Suggest a thoughtful reply to this forum topic discussion.",
        context=context,
    ))


@router.post("/summarize-topic")
@limiter.limit("3/minute")
def summarize_topic(
    request: Request,
    topic_id: int,
    current_user: User = Depends(get_current_user),
):
    """Generate a summary of a topic's discussion."""
    from boards.models import Post, Topic

    try:
        topic = Topic.objects.get(pk=topic_id)
    except Topic.DoesNotExist:
        raise HTTPException(status_code=404, detail="Topic not found")

    posts = Post.objects.filter(topic=topic).order_by('created_at')[:20]
    context = f"Topic: {topic.subject}\n\n"
    context += "\n".join([f"{p.created_by.username}: {p.message[:300]}" for p in posts])

    return _generate(ContentGenerateRequest(
        prompt="Summarize the key points and conclusions from this forum discussion.",
        context=context,
    ))
