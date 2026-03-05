"""
Pydantic schemas for API request/response models.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# =============================================================================
# USER
# =============================================================================

class UserBrief(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


# =============================================================================
# BOARDS
# =============================================================================

class BoardCreate(BaseModel):
    name: str
    description: str

class BoardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class BoardResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    posts_count: int = 0
    topics_count: int = 0
    last_post_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# TOPICS
# =============================================================================

class TopicCreate(BaseModel):
    subject: str
    message: str  # first post content

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
    updated_by: Optional[UserBrief] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


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
    results: List[SearchResult]


# =============================================================================
# CONTENT GENERATION
# =============================================================================

class ContentGenerateRequest(BaseModel):
    prompt: str
    context: Optional[str] = None  # e.g., topic subject, existing posts

class ContentGenerateResponse(BaseModel):
    generated_text: str
    model: str
    tokens_used: Optional[int] = None


# =============================================================================
# PAGINATION
# =============================================================================

class PaginatedResponse(BaseModel):
    count: int
    page: int
    page_size: int
    total_pages: int
    results: list
