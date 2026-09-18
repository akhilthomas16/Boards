"""
Post API endpoints — list, create, update, delete posts within topics.
"""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from django.contrib.auth.models import User
from django.db.models import Count, F
from django.db.models.functions import Greatest

from boards.models import Topic, Post
from ..auth import get_current_user
from ..schemas import PostCreate, PostListResponse, PostUpdate, PostResponse, UserBrief
from pydantic import BaseModel
from ..deps import paginate
from .profiles import get_user_badges

router = APIRouter()


def _posts(topic_id: int) -> "QuerySet[Post]":
    """Everything _post_to_response needs, without a query per post.

    order_by is explicit because aggregation drops Meta.ordering.
    """
    return (Post.objects.filter(topic_id=topic_id)
            .select_related("created_by__profile", "updated_by")
            .prefetch_related("reactions")
            .annotate(author_post_count=Count("created_by__posts", distinct=True))
            .order_by(*Post._meta.ordering))


def _post_to_response(post):
    reactions = {}
    for reaction in post.reactions.all():  # prefetched by _posts
        reactions[reaction.emoji] = reactions.get(reaction.emoji, 0) + 1

    return {
        "id": post.id,
        "message": post.message,
        "topic_id": post.topic_id,
        "created_by": {
            "id": post.created_by.id, 
            "username": post.created_by.username,
            "badges": get_user_badges(post.created_by.profile, getattr(post, "author_post_count", None))
        },
        "updated_by": (
            {"id": post.updated_by.id, "username": post.updated_by.username}
            if post.updated_by else None
        ),
        "reactions": reactions,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
    }


@router.get("/topic/{topic_id}", response_model=PostListResponse)
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

    paged = paginate(_posts(topic.id), page, page_size)
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
        
    return _post_to_response(post)


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


class ReactionRequest(BaseModel):
    emoji: Literal["👍", "❤️"]  # the reactions PostCard offers; widen together

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
            
    # 1 reaction from someone else = 1 reputation. Atomic, so concurrent reactions aren't lost.
    if post.created_by_id != current_user.id:
        from accounts.models import UserProfile
        change = F('reputation_score') + 1 if action == "added" else Greatest(F('reputation_score') - 1, 0)
        UserProfile.objects.filter(user_id=post.created_by_id).update(reputation_score=change)

    return {"status": "success", "action": action, "emoji": data.emoji}
