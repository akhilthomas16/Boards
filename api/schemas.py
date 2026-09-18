"""
Pydantic schemas for API request/response models.
"""
from datetime import datetime

from pydantic import BaseModel

# =============================================================================
# USER
# =============================================================================

class UserBrief(BaseModel):
    id: int
    username: str
    badges: list[str] = []

    class Config:
        from_attributes = True


# =============================================================================
# BOARDS
# =============================================================================

class BoardCreate(BaseModel):
    name: str
    description: str

class BoardUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

class BoardResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    posts_count: int = 0
    topics_count: int = 0
    last_post_at: datetime | None = None

    class Config:
        from_attributes = True


# =============================================================================
# TOPICS
# =============================================================================

class TopicCreate(BaseModel):
    subject: str
    message: str  # first post content
    tags: str | None = None

class TopicModerate(BaseModel):
    """Staff-only flags. Anything omitted is left alone."""
    is_pinned: bool | None = None
    is_locked: bool | None = None

class TopicResponse(BaseModel):
    id: int
    subject: str
    slug: str
    board_id: int
    board_name: str = ""
    starter: UserBrief
    views_count: int
    replies_count: int = 0
    is_pinned: bool
    is_locked: bool
    tags: str = ""
    last_updated: datetime

    class Config:
        from_attributes = True


# =============================================================================
# POSTS
# =============================================================================

class PostCreate(BaseModel):
    message: str

class PostUpdate(BaseModel):
    message: str

class PostResponse(BaseModel):
    id: int
    message: str
    topic_id: int
    created_by: UserBrief
    updated_by: UserBrief | None = None
    reactions: dict[str, int] = {}  # emoji → count
    my_reactions: list[str] = []  # emoji the caller has reacted with
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# =============================================================================
# PAGINATION
# =============================================================================

class Page(BaseModel):
    """What deps.paginate() returns around every list endpoint."""
    count: int
    page: int
    page_size: int
    total_pages: int

class BoardListResponse(Page):
    results: list[BoardResponse]

class TopicListResponse(Page):
    results: list[TopicResponse]

class PostListResponse(Page):
    results: list[PostResponse]


# =============================================================================
# SEARCH
# =============================================================================

class SearchResult(BaseModel):
    type: str  # "board", "topic", "post"
    id: int
    title: str
    snippet: str
    url: str


class SearchResponse(BaseModel):
    query: str
    total: int
    counts: dict[str, int]  # per type, for the search UI's tabs
    results: list[SearchResult]


# =============================================================================
# CONTENT GENERATION
# =============================================================================

class ContentGenerateRequest(BaseModel):
    prompt: str
    context: str | None = None  # e.g., topic subject, existing posts

class ContentGenerateResponse(BaseModel):
    generated_text: str
    model: str
    tokens_used: int | None = None


# =============================================================================
# PAGINATION
# =============================================================================

class PaginatedResponse(BaseModel):
    count: int
    page: int
    page_size: int
    total_pages: int
    results: list
