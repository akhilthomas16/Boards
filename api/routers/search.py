"""
Search across boards, topics and posts (Postgres LIKE via the ORM).
"""
from typing import Literal

from django.db.models import Q
from fastapi import APIRouter, Query

from ..schemas import SearchResponse, SearchResult

router = APIRouter()

SearchType = Literal["all", "board", "topic", "post"]


def _sections(q: str, type: SearchType):
    """(kind, queryset, row → SearchResult) for each type the query asks for, in display order."""
    from boards.models import Board, Post, Topic

    sections = [
        ("board", Board.objects.filter(Q(name__icontains=q) | Q(description__icontains=q)),
         lambda b: SearchResult(type="board", id=b.id, title=b.name, snippet=b.description[:200],
                                url=f"/boards/{b.id}")),
        ("topic", Topic.objects.filter(subject__icontains=q).select_related("board"),
         lambda t: SearchResult(type="topic", id=t.id, title=t.subject, snippet=f"in {t.board.name}",
                                url=f"/topics/{t.id}")),
        ("post", Post.objects.filter(message__icontains=q).select_related("topic"),
         lambda p: SearchResult(type="post", id=p.id, title=p.topic.subject, snippet=p.message[:200],
                                url=f"/topics/{p.topic_id}")),  # the post's topic, not the post id
    ]
    return [s for s in sections if type in ("all", s[0])]


@router.get("/", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=2, description="Search query"),
    type: SearchType = Query("all", description="Filter by type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Search boards, topics and posts. Results are one list, paginated across the types in order."""
    sections = _sections(q, type)
    counts = {kind: queryset.count() for kind, queryset, _ in sections}

    # Walk the sections, skipping whole ones until the requested page starts.
    skip = (page - 1) * page_size
    results = []
    for kind, queryset, to_result in sections:
        if len(results) == page_size:
            break
        if skip >= counts[kind]:
            skip -= counts[kind]
            continue
        rows = queryset[skip:skip + (page_size - len(results))]
        results.extend(to_result(row) for row in rows)
        skip = 0

    return SearchResponse(query=q, total=sum(counts.values()), counts=counts, results=results)
