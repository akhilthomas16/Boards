"""
Post API endpoints — list, create, update, delete posts within topics.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from django.contrib.auth.models import User

from boards.models import Topic, Post
from ..auth import get_current_user
from ..schemas import PostCreate, PostUpdate, PostResponse, UserBrief
from pydantic import BaseModel
from ..deps import paginate, invalidate_cache
from .profiles import get_user_badges

router = APIRouter()


def _post_to_response(post):
    # Aggregate reactions safely
    reactions = {}
    
    # We ideally would use `post.reactions.all()` if prefetched, otherwise count manually or by grouping wrapper. 
    # For performance, this would usually be annotated locally on QS, doing straightforward iter for now:
    for reaction in getattr(post, 'reactions_all', post.reactions.all()):
        reactions[reaction.emoji] = reactions.get(reaction.emoji, 0) + 1

    return {
        "id": post.id,
        "message": post.message,
        "topic_id": post.topic_id,
        "created_by": {
            "id": post.created_by.id, 
            "username": post.created_by.username,
            "badges": get_user_badges(post.created_by.profile)
        },
        "updated_by": (
            {"id": post.updated_by.id, "username": post.updated_by.username}
            if post.updated_by else None
        ),
        "reactions": reactions,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
    }


@router.get("/topic/{topic_id}")
def list_posts(
    topic_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List posts in a topic with pagination."""
    try:
        topic = Topic.objects.get(pk=topic_id)
    except Topic.DoesNotExist:
        raise HTTPException(status_code=404, detail="Topic not found")

    qs = Post.objects.filter(topic=topic).select_related('created_by', 'updated_by').prefetch_related('reactions')
    paged = paginate(qs, page, page_size)
    paged["results"] = [_post_to_response(p) for p in paged["results"]]
    return paged


@router.post("/topic/{topic_id}", status_code=status.HTTP_201_CREATED)
def create_post(
    topic_id: int,
    data: PostCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new post/reply in a topic."""
    try:
        topic = Topic.objects.get(pk=topic_id)
    except Topic.DoesNotExist:
        raise HTTPException(status_code=404, detail="Topic not found")

    if topic.is_locked:
        raise HTTPException(status_code=403, detail="This topic is locked")

    post = Post.objects.create(
        message=data.message,
        topic=topic,
        created_by=current_user,
    )
    
    # Notify topic starter
    if topic.starter != current_user:
        from notifications.models import Notification
        Notification.objects.create(
            recipient=topic.starter,
            actor=current_user,
            message=f"replied to your topic: {topic.subject[:30]}",
            link=f"/topics/{topic.id}#post-{post.id}"
        )
        
    invalidate_cache("posts")
    return _post_to_response(post)


@router.post("/topic/{topic_id}/htmx", response_class=HTMLResponse)
def create_post_htmx(
    topic_id: int,
    data: PostCreate,
    current_user: User = Depends(get_current_user),
):
    """HTMX endpoint — create post and return HTML partial."""
    try:
        topic = Topic.objects.get(pk=topic_id)
    except Topic.DoesNotExist:
        return HTMLResponse('<div class="alert alert-danger">Topic not found</div>', status_code=404)

    if topic.is_locked:
        return HTMLResponse('<div class="alert alert-warning">This topic is locked</div>', status_code=403)

    post = Post.objects.create(
        message=data.message,
        topic=topic,
        created_by=current_user,
    )
    
    # Notify topic starter
    if topic.starter != current_user:
        from notifications.models import Notification
        Notification.objects.create(
            recipient=topic.starter,
            actor=current_user,
            message=f"replied to your topic: {topic.subject[:30]}",
            link=f"/topics/{topic.id}#post-{post.id}"
        )
        
    invalidate_cache("posts")

    return HTMLResponse(f"""
        <div class="post-card fade-in" id="post-{post.id}">
            <div class="post-header">
                <strong>{current_user.username}</strong>
                <span class="text-muted">just now</span>
            </div>
            <div class="post-body">{post.message}</div>
        </div>
    """)


@router.patch("/{post_id}")
def update_post(
    post_id: int,
    data: PostUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update a post (only by the author)."""
    try:
        post = Post.objects.select_related('created_by').get(pk=post_id)
    except Post.DoesNotExist:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.created_by.id != current_user.id and not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Can only edit your own posts")

    post.message = data.message
    post.updated_by = current_user
    post.updated_at = datetime.now(timezone.utc)
    post.save()
    invalidate_cache("posts")
    return _post_to_response(post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete a post (author or staff only)."""
    try:
        post = Post.objects.select_related('created_by').get(pk=post_id)
    except Post.DoesNotExist:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.created_by.id != current_user.id and not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Can only delete your own posts")

    post.delete()
    invalidate_cache("posts")


class ReactionRequest(BaseModel):
    emoji: str

@router.post("/{post_id}/react")
def toggle_reaction(
    post_id: int,
    data: ReactionRequest,
    current_user: User = Depends(get_current_user),
):
    """Toggle an emoji reaction on a post."""
    from boards.models import Reaction
    
    try:
        post = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        raise HTTPException(status_code=404, detail="Post not found")
        
    reaction, created = Reaction.objects.get_or_create(
        user=current_user,
        post=post,
        emoji=data.emoji
    )
    
    if not created:
        # If it already existed, toggle it off
        reaction.delete()
        action = "removed"
    else:
        action = "added"
        # Notify the post author
        if post.created_by != current_user:
            from notifications.models import Notification
            Notification.objects.create(
                recipient=post.created_by,
                actor=current_user,
                message=f"reacted {data.emoji} to your post",
                link=f"/topics/{post.topic.id}#post-{post.id}"
            )
            
    # Calculate new reputation score (dummy example: 1 reaction = +1 rep)
    # This could be handled via signals, but simple straight calculation here:
    if action == "added":
        profile = post.created_by.profile
        profile.reputation_score = (profile.reputation_score or 0) + 1
        profile.save(update_fields=["reputation_score"])
    elif action == "removed":
        profile = post.created_by.profile
        profile.reputation_score = max(0, (profile.reputation_score or 0) - 1)
        profile.save(update_fields=["reputation_score"])

    invalidate_cache(f"topic_{post.topic.id}")
    return {"status": "success", "action": action, "emoji": data.emoji}
