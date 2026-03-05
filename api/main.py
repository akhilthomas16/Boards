"""
FastAPI application — REST API for the Boards forum.
Run separately: uvicorn api.main:app --port 8001 --reload
"""
import os
import django

# Bootstrap Django ORM before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from decouple import config, Csv
import os

from .limiter import limiter
from .routers import boards, topics, posts, search, content, profiles, notifications, upload
from .auth import router as auth_router

app = FastAPI(
    title="Boards Forum API",
    description="REST API for the Boards web forum with JWT authentication",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000', cast=Csv()),
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

# Serve uploaded media files
media_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'media')
if os.path.exists(media_dir):
    app.mount("/media", StaticFiles(directory=media_dir), name="media")


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "boards-api"}
