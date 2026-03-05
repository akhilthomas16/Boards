"""
LLM content generation endpoints — topic summaries, reply suggestions.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from django.contrib.auth.models import User
from django.conf import settings

from ..auth import get_current_user
from ..schemas import ContentGenerateRequest, ContentGenerateResponse
from ..tasks import generate_content_task

from ..main import limiter

router = APIRouter()


@router.post("/generate", response_model=ContentGenerateResponse)
@limiter.limit("5/minute")
async def generate_content(
    request: Request,
    data: ContentGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate content using LLM (synchronous, for short completions)."""
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="LLM service not configured")

    try:
        import openai
        client = openai.OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

        system_prompt = (
            "You are a helpful forum assistant. Generate content that is "
            "informative, well-structured, and appropriate for a discussion board. "
            "Keep responses concise and relevant."
        )

        messages = [{"role": "system", "content": system_prompt}]

        if data.context:
            messages.append({"role": "user", "content": f"Context: {data.context}"})

        messages.append({"role": "user", "content": data.prompt})

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )

        return ContentGenerateResponse(
            generated_text=response.choices[0].message.content,
            model=settings.OPENAI_MODEL,
            tokens_used=response.usage.total_tokens if response.usage else None,
        )

    except openai.APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")


@router.post("/suggest-reply")
@limiter.limit("3/minute")
async def suggest_reply(
    request: Request,
    topic_id: int,
    current_user: User = Depends(get_current_user),
):
    """Generate a suggested reply based on topic context."""
    from boards.models import Topic, Post

    try:
        topic = Topic.objects.get(pk=topic_id)
    except Topic.DoesNotExist:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Gather context from existing posts
    posts = Post.objects.filter(topic=topic).order_by('-created_at')[:5]
    context = f"Topic: {topic.subject}\n\n"
    context += "\n".join([f"{p.created_by.username}: {p.message[:200]}" for p in posts])

    request = ContentGenerateRequest(
        prompt="Suggest a thoughtful reply to this forum topic discussion.",
        context=context,
    )
    return await generate_content(request, current_user)


@router.post("/summarize-topic")
@limiter.limit("3/minute")
async def summarize_topic(
    request: Request,
    topic_id: int,
    current_user: User = Depends(get_current_user),
):
    """Generate a summary of a topic's discussion."""
    from boards.models import Topic, Post

    try:
        topic = Topic.objects.get(pk=topic_id)
    except Topic.DoesNotExist:
        raise HTTPException(status_code=404, detail="Topic not found")

    posts = Post.objects.filter(topic=topic).order_by('created_at')[:20]
    context = f"Topic: {topic.subject}\n\n"
    context += "\n".join([f"{p.created_by.username}: {p.message[:300]}" for p in posts])

    request = ContentGenerateRequest(
        prompt="Summarize the key points and conclusions from this forum discussion.",
        context=context,
    )
    return await generate_content(request, current_user)
