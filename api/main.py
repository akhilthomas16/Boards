"""
FastAPI application — REST API for the Hash Out forum.
Run separately: uvicorn api.main:app --port 8001 --reload
"""
import os

import django

# Bootstrap Django ORM before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hash_out.settings')
django.setup()

from django.conf import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .auth import router as auth_router
from .limiter import limiter
from .routers import boards, content, notifications, posts, profiles, search, topics, upload

app = FastAPI(
    title="Hash Out API",
    description="REST API for the Hash Out discussion forum with JWT authentication",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(boards.router, prefix="/api/boards", tags=["Boards"])
app.include_router(topics.router, prefix="/api/topics", tags=["Topics"])
app.include_router(posts.router, prefix="/api/posts", tags=["Posts"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(content.router, prefix="/api/content", tags=["Content Generation"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["User Profiles"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(upload.router, prefix="/api/upload", tags=["Uploads"])

class MediaFiles(StaticFiles):
    """User uploads: never sniffed, never scripted, and only image types served as images."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
        if not response.headers.get("content-type", "").startswith(("image/jpeg", "image/png", "image/gif", "image/webp")):
            response.headers["Content-Type"] = "application/octet-stream"
        return response


# Serve uploaded media files
media_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'media')
if os.path.exists(media_dir):
    app.mount("/media", MediaFiles(directory=media_dir), name="media")


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "hash-out-api"}
