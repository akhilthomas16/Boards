"""
Topic API endpoints — list, create, retrieve topics within boards.
"""
from functools import reduce
from operator import or_

from django.db.models import Q
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from django.contrib.auth.models import User

from boards.models import Board, Topic, Post
from ..auth import get_current_user
from ..schemas import TopicCreate, TopicResponse, UserBrief
from ..deps import paginate, invalidate_cache

router = APIRouter()


def _normalize_tags(raw: str | None) -> str:
    """Comma-separated, lowercased, de-duplicated, order preserved."""
    seen = []
    for tag in (raw or "").split(","):
        tag = tag.strip().lower()
        if tag and tag not in seen:
            seen.append(tag)
    return ",".join(seen)[:255]


def _topic_to_response(topic: Topic) -> dict:
    """Convert a Topic model to response dict."""
    return {
        "id": topic.id,
        "subject": topic.subject,
        "slug": topic.slug,
        "board_id": topic.board_id,
        "board_name": topic.board.name,
        "starter": {"id": topic.starter.id, "username": topic.starter.username},
        "views_count": topic.views_count,
        "replies_count": max(0, topic.posts.count() - 1),
        "is_pinned": topic.is_pinned,
        "is_locked": topic.is_locked,
        "tags": topic.tags,
        "last_updated": topic.last_updated,
    }


@router.get("/trending")
def trending_topics():
    """Get trending topics based on views and updates."""
    # Simple algorithm: order by views_count locally. For real prod: (views_count + (replies * 5)) over last 7 days.
    qs = Topic.objects.all().select_related('starter', 'board').order_by('-views_count', '-last_updated')[:5]
    return [_topic_to_response(t) for t in qs]


@router.get("/{topic_id}/similar")
def similar_topics(topic_id: int):
    """Find similar topics via simple tags overlap or same board."""
    try:
        topic = Topic.objects.get(pk=topic_id)
    except Topic.DoesNotExist:
        raise HTTPException(status_code=404, detail="Topic not found")
        
    siblings = Topic.objects.exclude(id=topic_id).select_related('starter', 'board')

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



@router.get("/board/{board_id}")
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

    qs = Topic.objects.filter(board=board).select_related('starter', 'board')
    paged = paginate(qs, page, page_size)
    paged["results"] = [_topic_to_response(t) for t in paged["results"]]
    return paged


@router.get("/{topic_id}", response_model=TopicResponse)
def get_topic(topic_id: int):
    """Get a single topic and increment view count."""
    try:
        topic = Topic.objects.select_related('starter', 'board').get(pk=topic_id)
    except Topic.DoesNotExist:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Increment views
    Topic.objects.filter(pk=topic_id).update(views_count=topic.views_count + 1)
    topic.views_count += 1

    return _topic_to_response(topic)


@router.post("/board/{board_id}", status_code=status.HTTP_201_CREATED)
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
    Post.objects.create(
        message=data.message,
        topic=topic,
        created_by=current_user,
    )
    invalidate_cache("topics")
    return _topic_to_response(topic)


@router.post("/board/{board_id}/htmx", response_class=HTMLResponse)
def create_topic_htmx(
    board_id: int,
    data: TopicCreate,
    current_user: User = Depends(get_current_user),
):
    """HTMX endpoint — create topic and return HTML partial."""
    try:
        board = Board.objects.get(pk=board_id)
    except Board.DoesNotExist:
        return HTMLResponse(
            '<div class="alert alert-danger">Board not found</div>',
            status_code=404,
        )

    topic = Topic.objects.create(
        subject=data.subject,
        board=board,
        starter=current_user,
    )
    Post.objects.create(
        message=data.message,
        topic=topic,
        created_by=current_user,
    )
    invalidate_cache("topics")

    # Return HTML partial for HTMX swap
    return HTMLResponse(f"""
        <tr class="fade-in">
            <td><a href="/topics/{topic.id}">{topic.subject}</a></td>
            <td>{current_user.username}</td>
            <td>0</td>
            <td>0</td>
            <td>just now</td>
        </tr>
    """)
