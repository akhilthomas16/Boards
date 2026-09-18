"""
Notifications router — handles WebSockets and notification CRUD.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from starlette.concurrency import run_in_threadpool
import asyncio
import contextlib
import redis.asyncio as aioredis
from django.conf import settings
from pydantic import BaseModel
from typing import List
from datetime import datetime
import json
import logging

from ..auth import ACCESS_COOKIE, get_current_user, user_from_token
from ..deps import paginate
from ..schemas import Page
from fastapi import Query
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)
router = APIRouter()


class NotificationResponse(BaseModel):
    id: int
    message: str
    link: str
    actor: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(Page):
    results: List[NotificationResponse]


class UnreadCount(BaseModel):
    unread: int


def _as_response(n) -> NotificationResponse:
    return NotificationResponse(id=n.id, message=n.message, link=n.link,
                                actor=n.actor.username, is_read=n.is_read, created_at=n.created_at)


@router.get("/", response_model=NotificationListResponse)
def get_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """The current user's notifications, newest first."""
    from notifications.models import Notification

    paged = paginate(Notification.objects.filter(recipient=current_user).select_related('actor'),
                     page, page_size)
    paged["results"] = [_as_response(n) for n in paged["results"]]
    return paged


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(current_user: User = Depends(get_current_user)):
    """How many unread notifications the user has — one query, no list."""
    from notifications.models import Notification
    return {"unread": Notification.objects.filter(recipient=current_user, is_read=False).count()}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(notification_id: int, current_user: User = Depends(get_current_user)):
    """Mark a notification as read."""
    from notifications.models import Notification
    notification = Notification.objects.filter(id=notification_id, recipient=current_user).select_related('actor').first()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    return _as_response(notification)


@router.post("/read-all", response_model=UnreadCount)
def mark_all_read(current_user: User = Depends(get_current_user)):
    """Mark everything read in one query (the client used to send one request per notification)."""
    from notifications.models import Notification
    Notification.objects.filter(recipient=current_user, is_read=False).update(is_read=True)
    return {"unread": 0}


@router.delete("/{notification_id}", status_code=204)
def delete_notification(notification_id: int, current_user: User = Depends(get_current_user)):
    """Delete one notification."""
    from notifications.models import Notification
    deleted, _ = Notification.objects.filter(id=notification_id, recipient=current_user).delete()
    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")


@router.websocket("/ws")
async def websocket_notifications(websocket: WebSocket):
    """
    WebSocket endpoint for real-time notifications, authenticated by the access-token cookie.
    Auth and Origin are checked before accept(), so a bad handshake is rejected with 403.
    """
    if websocket.headers.get("origin") not in settings.CORS_ALLOWED_ORIGINS:
        await websocket.close(code=1008)
        return
    try:
        user = await run_in_threadpool(user_from_token, websocket.cookies.get(ACCESS_COOKIE))
    except HTTPException:
        await websocket.close(code=1008)
        return

    # ponytail: auth is checked at connect only; a user deactivated mid-connection keeps receiving
    # their own notifications until the socket reconnects.
    await websocket.accept()
    channel_name = f"user_{user.id}_notifications"
    r = aioredis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()

    async def forward_notifications():
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"].decode("utf-8"))

    async def wait_for_disconnect():
        # The client never sends anything; receiving is how a closed tab is noticed.
        while (await websocket.receive())["type"] != "websocket.disconnect":
            pass

    try:
        await pubsub.subscribe(channel_name)
        done, pending = await asyncio.wait(
            [asyncio.create_task(forward_notifications()), asyncio.create_task(wait_for_disconnect())],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            task.result()  # re-raise a Redis or send failure
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Notification socket for user %s failed", user.id)
        with contextlib.suppress(Exception):  # the client may already be gone
            await websocket.close(code=1011)
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.aclose()
        await r.aclose()
