"""
User profile API endpoints — view profile, update profile, upload avatar.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from pydantic import BaseModel
from typing import Optional

from ..auth import get_current_user

router = APIRouter()


class ProfileResponse(BaseModel):
    user_id: int
    username: str
    email: str
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


class ProfileUpdate(BaseModel):
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None


def get_user_badges(profile) -> list[str]:
    badges = []
    if profile.reputation_score >= 100:
        badges.append("Legend")
    elif profile.reputation_score >= 10:
        badges.append("Contributor")
        
    if profile.post_count >= 50:
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

@router.get("/search/users", response_model=list[ProfileResponse])
def search_users(q: str = ""):
    """Search users by username for mentions autocomplete."""
    if not q:
        return []
    users = User.objects.filter(username__icontains=q).select_related('profile')[:5]
    return [_profile_to_response(u) for u in users]

@router.get("/{username}", response_model=ProfileResponse)
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
        profile.website = data.website
    profile.save()
    return _profile_to_response(current_user)


@router.post("/me/avatar", response_model=ProfileResponse)
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a profile avatar image."""
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # Validate file size (max 2MB)
    contents = file.file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 2MB.")

    profile = current_user.profile

    # Delete old avatar
    if profile.avatar:
        profile.avatar.delete(save=False)

    # Save new avatar
    filename = f"{current_user.username}_{file.filename}"
    profile.avatar.save(filename, ContentFile(contents), save=True)

    return _profile_to_response(current_user)
