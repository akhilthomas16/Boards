"""
Board API endpoints — list, retrieve, create, update, delete boards.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from django.contrib.auth.models import User

from boards.models import Board
from ..auth import get_current_user
from ..schemas import BoardCreate, BoardUpdate, BoardResponse
from ..deps import paginate, invalidate_cache

router = APIRouter()


def _board_to_response(board: Board) -> dict:
    """Convert a Board model to response dict."""
    last_post = board.get_last_post()
    return {
        "id": board.id,
        "name": board.name,
        "slug": board.slug,
        "description": board.description,
        "posts_count": board.get_posts_count(),
        "topics_count": board.topics.count(),
        "last_post_at": last_post.created_at if last_post else None,
    }


@router.get("/")
async def list_boards(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    """List all boards with pagination."""
    qs = Board.objects.all()
    paged = paginate(qs, page, page_size)
    paged["results"] = [_board_to_response(b) for b in paged["results"]]
    return paged


@router.get("/{board_id}", response_model=BoardResponse)
async def get_board(board_id: int):
    """Get a single board by ID."""
    try:
        board = Board.objects.get(pk=board_id)
    except Board.DoesNotExist:
        raise HTTPException(status_code=404, detail="Board not found")
    return _board_to_response(board)


@router.get("/slug/{slug}", response_model=BoardResponse)
async def get_board_by_slug(slug: str):
    """Get a single board by slug."""
    try:
        board = Board.objects.get(slug=slug)
    except Board.DoesNotExist:
        raise HTTPException(status_code=404, detail="Board not found")
    return _board_to_response(board)


@router.post("/", response_model=BoardResponse, status_code=status.HTTP_201_CREATED)
async def create_board(data: BoardCreate, current_user: User = Depends(get_current_user)):
    """Create a new board (authenticated users only)."""
    if not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Only staff can create boards")
    if Board.objects.filter(name=data.name).exists():
        raise HTTPException(status_code=400, detail="Board with this name already exists")
    board = Board.objects.create(name=data.name, description=data.description)
    invalidate_cache("boards")
    return _board_to_response(board)


@router.patch("/{board_id}", response_model=BoardResponse)
async def update_board(board_id: int, data: BoardUpdate, current_user: User = Depends(get_current_user)):
    """Update a board (staff only)."""
    if not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Only staff can update boards")
    try:
        board = Board.objects.get(pk=board_id)
    except Board.DoesNotExist:
        raise HTTPException(status_code=404, detail="Board not found")

    if data.name is not None:
        board.name = data.name
    if data.description is not None:
        board.description = data.description
    board.save()
    invalidate_cache("boards")
    return _board_to_response(board)


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(board_id: int, current_user: User = Depends(get_current_user)):
    """Delete a board (staff only)."""
    if not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Only staff can delete boards")
    try:
        board = Board.objects.get(pk=board_id)
    except Board.DoesNotExist:
        raise HTTPException(status_code=404, detail="Board not found")

    if board.topics.exists():
        raise HTTPException(status_code=400, detail="Cannot delete board with existing topics")
    board.delete()
    invalidate_cache("boards")
