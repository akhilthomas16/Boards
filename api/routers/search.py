"""
Elasticsearch-powered search endpoint.
"""
from fastapi import APIRouter, Query, HTTPException
from ..schemas import SearchResponse, SearchResult

router = APIRouter()


@router.get("/", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=2, description="Search query"),
    type: str = Query("all", description="Filter by type: all, board, topic, post"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Search boards, topics, and posts using Elasticsearch.
    Falls back to Django ORM if Elasticsearch is unavailable.
    """
    results = []
    offset = (page - 1) * page_size

    try:
        # Try Elasticsearch first
        results, total = _search_elasticsearch(q, type, offset, page_size)
    except Exception:
        # Fallback to Django ORM search
        results, total = _search_orm(q, type, offset, page_size)

    return SearchResponse(query=q, total=total, results=results)


def _search_elasticsearch(q: str, type: str, offset: int, limit: int):
    """Search using Elasticsearch DSL."""
    from boards.documents import BoardDocument, TopicDocument, PostDocument

    results = []
    total = 0

    if type in ("all", "board"):
        s = BoardDocument.search().query("multi_match", query=q, fields=["name", "description"])
        s = s[offset:offset + limit]
        response = s.execute()
        total += response.hits.total.value
        for hit in response:
            results.append(SearchResult(
                type="board",
                id=hit.meta.id,
                title=hit.name,
                snippet=hit.description[:200],
                url=f"/boards/{hit.meta.id}",
            ))

    if type in ("all", "topic"):
        s = TopicDocument.search().query("multi_match", query=q, fields=["subject", "board_name"])
        s = s[offset:offset + limit]
        response = s.execute()
        total += response.hits.total.value
        for hit in response:
            results.append(SearchResult(
                type="topic",
                id=hit.meta.id,
                title=hit.subject,
                snippet=f"in {hit.board_name}" if hasattr(hit, 'board_name') else "",
                url=f"/topics/{hit.meta.id}",
            ))

    if type in ("all", "post"):
        s = PostDocument.search().query("multi_match", query=q, fields=["message", "topic_subject"])
        s = s[offset:offset + limit]
        response = s.execute()
        total += response.hits.total.value
        for hit in response:
            results.append(SearchResult(
                type="post",
                id=hit.meta.id,
                title=hit.topic_subject if hasattr(hit, 'topic_subject') else "Post",
                snippet=hit.message[:200] if hasattr(hit, 'message') else "",
                url=f"/topics/{hit.meta.id}",
            ))

    return results, total


def _search_orm(q: str, type: str, offset: int, limit: int):
    """Fallback search using Django ORM (LIKE queries)."""
    from boards.models import Board, Topic, Post

    results = []
    total = 0

    if type in ("all", "board"):
        boards = Board.objects.filter(name__icontains=q) | Board.objects.filter(description__icontains=q)
        total += boards.count()
        for b in boards[offset:offset + limit]:
            results.append(SearchResult(
                type="board", id=b.id, title=b.name, snippet=b.description[:200],
                url=f"/boards/{b.id}",
            ))

    if type in ("all", "topic"):
        topics = Topic.objects.filter(subject__icontains=q).select_related('board')
        total += topics.count()
        for t in topics[offset:offset + limit]:
            results.append(SearchResult(
                type="topic", id=t.id, title=t.subject, snippet=f"in {t.board.name}",
                url=f"/topics/{t.id}",
            ))

    if type in ("all", "post"):
        posts = Post.objects.filter(message__icontains=q).select_related('topic')
        total += posts.count()
        for p in posts[offset:offset + limit]:
            results.append(SearchResult(
                type="post", id=p.id, title=p.topic.subject,
                snippet=p.message[:200], url=f"/topics/{p.topic.id}",
            ))

    return results, total
