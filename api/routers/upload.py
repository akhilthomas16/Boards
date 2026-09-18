"""
Upload endpoints for generic media (e.g., images dropped into the Markdown editor).
"""
import io
import os
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from PIL import Image

from ..auth import get_current_user
from ..limiter import limiter

router = APIRouter()

UPLOAD_DIR = os.path.join(settings.BASE_DIR, 'media', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Pillow's detected format → stored extension. The client's filename and Content-Type are never trusted.
IMAGE_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "GIF": ".gif", "WEBP": ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def read_image(file: UploadFile, max_bytes: int) -> tuple[bytes, str]:
    """Return (bytes, extension) for a real JPEG/PNG/GIF/WEBP no larger than max_bytes, else 400."""
    # ponytail: Starlette has already spooled the whole body; cap request size at the proxy (Phase 7).
    contents = file.file.read(max_bytes + 1)
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {max_bytes // (1024 * 1024)}MB.")
    try:
        with Image.open(io.BytesIO(contents)) as image:
            image_format = image.format
            image.verify()
    except Exception:
        image_format = None
    if image_format not in IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, GIF, and WEBP images are allowed.")
    return contents, IMAGE_EXTENSIONS[image_format]


@router.post("/image")
@limiter.limit("10/minute")
def upload_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload an image to be used in a markdown post."""
    contents, ext = read_image(file, MAX_FILE_SIZE)
    filename = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOAD_DIR, filename), "wb") as buffer:
        buffer.write(contents)

    return {"url": f"{settings.MEDIA_URL}uploads/{filename}"}
