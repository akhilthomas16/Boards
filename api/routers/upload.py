"""
Upload endpoints for generic media (e.g., images dropped into the Markdown editor).
"""
import os
import shutil
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from django.conf import settings
from django.contrib.auth.models import User

from ..auth import get_current_user
from ..main import limiter

router = APIRouter()

UPLOAD_DIR = os.path.join(settings.BASE_DIR, 'media', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/image")
@limiter.limit("10/minute")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload an image to be used in a markdown post."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, GIF, and WEBP images are allowed.")

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")

    # Generate unique filename
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"url": f"{settings.MEDIA_URL}uploads/{filename}"}
