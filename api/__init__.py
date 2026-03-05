"""
FastAPI application — REST API for the Boards forum.
Run separately: uvicorn api.main:app --port 8001 --reload
"""
import os
import django

# Bootstrap Django ORM before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from decouple import config, Csv

from .routers import boards, topics, posts, search, content
from .auth import router as auth_router

app = FastAPI(
    title="Boards Forum API",
    description="REST API for the Boards web forum with JWT authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

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


@app.get("/api/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "boards-api"}
