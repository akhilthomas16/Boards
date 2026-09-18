"""
User profile API endpoints — view profile, update profile, upload avatar.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request
from django.contrib.auth.models import User
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import URLValidator
from pydantic import BaseModel
from typing import Optional

from ..auth import get_current_user
from ..limiter import limiter
from .upload import read_image

router = APIRouter()


class PublicProfileResponse(BaseModel):
    """What anyone can see. FastAPI drops every field not declared here, including email."""
    user_id: int
    username: str
    bio: str
    avatar_url: Optional[str]
    location: str
    website: str
    post_count: int
    topic_count: int
    reputation_score: int
    badges: list[str]
    date_joined: str

    class Config:
        from_attributes = True


class ProfileResponse(PublicProfileResponse):
    """The owner's own view."""
    email: str


class ProfileUpdate(BaseModel):
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None


def get_user_badges(profile, post_count: int | None = None) -> list[str]:
    """`post_count` skips the per-profile COUNT when the caller already annotated it."""
    if post_count is None:
        post_count = profile.post_count

    badges = []
    if profile.reputation_score >= 100:
        badges.append("Legend")
    elif profile.reputation_score >= 10:
        badges.append("Contributor")

    if post_count >= 50:
        badges.append("Top Poster")
        
    if not badges:
        badges.append("Newbie")
    return badges

def _profile_to_response(user: User) -> dict:
    profile = user.profile
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "bio": profile.bio,
        "avatar_url": profile.avatar_url,
        "location": profile.location,
        "website": profile.website,
        "post_count": profile.post_count,
        "topic_count": profile.topic_count,
        "reputation_score": profile.reputation_score,
        "badges": get_user_badges(profile),
        "date_joined": user.date_joined.isoformat(),
    }


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return _profile_to_response(current_user)

@router.get("/search/users", response_model=list[PublicProfileResponse])
@limiter.limit("30/minute")
def search_users(request: Request, q: str = Query(..., min_length=2)):
    """Search users by username for mentions autocomplete."""
    users = User.objects.filter(username__icontains=q).select_related('profile')[:5]
    return [_profile_to_response(u) for u in users]

@router.get("/{username}", response_model=PublicProfileResponse)
def get_profile(username: str):
    """Get a user's public profile by username."""
    try:
        user = User.objects.select_related('profile').get(username=username)
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    return _profile_to_response(user)


@router.patch("/me", response_model=ProfileResponse)
def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update the current user's profile."""
    profile = current_user.profile
    if data.bio is not None:
        profile.bio = data.bio
    if data.location is not None:
        profile.location = data.location
    if data.website is not None:
        # Rendered as a link: anything but http(s) (javascript:, data:) is an XSS vector.
        try:
            if data.website:
                URLValidator(schemes=["http", "https"])(data.website)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Website must be an http:// or https:// URL")
        profile.website = data.website
    profile.save()
    return _profile_to_response(current_user)


@router.post("/me/avatar", response_model=ProfileResponse)
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a profile avatar image."""
    contents, ext = read_image(file, 2 * 1024 * 1024)
    profile = current_user.profile

    # Delete old avatar
    if profile.avatar:
        profile.avatar.delete(save=False)

    # Save new avatar. A fresh name per upload, so browsers don't keep showing the cached old one.
    filename = f"{uuid.uuid4().hex}{ext}"
    profile.avatar.save(filename, ContentFile(contents), save=True)

    return _profile_to_response(current_user)
