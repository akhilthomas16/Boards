"""
Topic API endpoints — list, create, retrieve topics within boards.
"""
from functools import reduce
from operator import or_

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, F, Q, QuerySet
from fastapi import APIRouter, Depends, HTTPException, Query, status

from boards.models import Board, Post, Topic

from ..auth import get_current_user
from ..deps import paginate
from ..mentions import notify_mentions
from ..schemas import TopicCreate, TopicListResponse, TopicModerate, TopicResponse

router = APIRouter()


def _normalize_tags(raw: str | None) -> str:
    """Comma-separated, lowercased, de-duplicated, order preserved."""
    seen = []
    for tag in (raw or "").split(","):
        tag = tag.strip().lower()
        if tag and tag not in seen:
            seen.append(tag)
    return ",".join(seen)[:255]


def _topics() -> QuerySet[Topic]:
    """Reply count as an annotation: one query for any number of topics.

    order_by is explicit because aggregation drops Meta.ordering.
    """
    return (Topic.objects.select_related("board", "starter")
            .annotate(posts_total=Count("posts"))
            .order_by(*Topic._meta.ordering))


def _topic_to_response(topic: Topic) -> dict:
    """Convert a Topic (annotated by _topics, or plain) to a response dict."""
    posts_total = getattr(topic, "posts_total", None)
    if posts_total is None:
        posts_total = topic.posts.count()
    return {
        "id": topic.id,
        "subject": topic.subject,
        "slug": topic.slug,
        "board_id": topic.board_id,
        "board_name": topic.board.name,
        "starter": {"id": topic.starter.id, "username": topic.starter.username},
        "views_count": topic.views_count,
        "replies_count": max(0, posts_total - 1),  # the first post is the topic itself
        "is_pinned": topic.is_pinned,
        "is_locked": topic.is_locked,
        "tags": topic.tags,
        "last_updated": topic.last_updated,
    }


@router.get("/trending", response_model=list[TopicResponse])
def trending_topics():
    """Get trending topics based on views and updates."""
    # Simple algorithm: order by views_count locally. For real prod: (views_count + (replies * 5)) over last 7 days.
    qs = _topics().order_by('-views_count', '-last_updated')[:5]
    return [_topic_to_response(t) for t in qs]


@router.get("/{topic_id}/similar", response_model=list[TopicResponse])
def similar_topics(topic_id: int):
    """Find similar topics via simple tags overlap or same board."""
    try:
        topic = Topic.objects.get(pk=topic_id)
    except Topic.DoesNotExist:
        raise HTTPException(status_code=404, detail="Topic not found")
        
    siblings = _topics().exclude(id=topic_id)

    tags = [t for t in topic.tags.split(",") if t]
    if tags:
        overlapping = siblings.filter(
            reduce(or_, (Q(tags__contains=tag) for tag in tags))
        ).order_by('-last_updated')[:5]
        matches = list(overlapping)
    else:
        matches = []

    if len(matches) < 5:
        # Top up with recent topics from the same board.
        seen = {t.id for t in matches}
        fill = siblings.filter(board=topic.board).exclude(id__in=seen).order_by('-last_updated')
        matches += list(fill[:5 - len(matches)])

    return [_topic_to_response(t) for t in matches]



@router.get("/board/{board_id}", response_model=TopicListResponse)
def list_topics(
    board_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List topics for a board with pagination."""
    try:
        board = Board.objects.get(pk=board_id)
    except Board.DoesNotExist:
        raise HTTPException(status_code=404, detail="Board not found")

    qs = _topics().filter(board=board)
    paged = paginate(qs, page, page_size)
    paged["results"] = [_topic_to_response(t) for t in paged["results"]]
    return paged


@router.get("/{topic_id}", response_model=TopicResponse)
def get_topic(topic_id: int):
    """Get a single topic and increment view count."""
    try:
        topic = _topics().get(pk=topic_id)
    except Topic.DoesNotExist:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Increment views
    Topic.objects.filter(pk=topic_id).update(views_count=F('views_count') + 1)
    topic.views_count += 1

    return _topic_to_response(topic)


@router.post("/board/{board_id}", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(
    board_id: int,
    data: TopicCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new topic with an initial post (authenticated only)."""
    try:
        board = Board.objects.get(pk=board_id)
    except Board.DoesNotExist:
        raise HTTPException(status_code=404, detail="Board not found")

    topic = Topic.objects.create(
        subject=data.subject,
        board=board,
        starter=current_user,
        tags=_normalize_tags(data.tags),
    )
    post = Post.objects.create(
        message=data.message,
        topic=topic,
        created_by=current_user,
    )
    notify_mentions(data.message, current_user, f"/topics/{topic.id}#post-{post.id}")
    return _topic_to_response(topic)


def _staff_only(user: User) -> None:
    if not user.is_staff:
        raise HTTPException(status_code=403, detail="Moderator access required")


@router.patch("/{topic_id}", response_model=TopicResponse)
def moderate_topic(
    topic_id: int,
    data: TopicModerate,
    current_user: User = Depends(get_current_user),
):
    """Pin or lock a topic (staff only)."""
    _staff_only(current_user)
    topic = _topics().filter(pk=topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    fields = data.model_dump(exclude_unset=True)
    if fields:
        Topic.objects.filter(pk=topic_id).update(**fields)  # .update(): no auto_now bump on last_updated
        topic = _topics().get(pk=topic_id)
    return _topic_to_response(topic)


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(topic_id: int, current_user: User = Depends(get_current_user)):
    """Delete a topic and its posts (staff only)."""
    _staff_only(current_user)
    topic = Topic.objects.filter(pk=topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    with transaction.atomic():
        # Post.topic is PROTECT, so the posts (and their cascading reactions) go first.
        Post.objects.filter(topic=topic).delete()
        topic.delete()
