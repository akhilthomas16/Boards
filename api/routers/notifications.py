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


@router.get("/", response_model=List[NotificationResponse])
def get_notifications(current_user: User = Depends(get_current_user)):
    """Get the latest notifications for the current user."""
    from notifications.models import Notification
    
    # Get last 20 notifications
    notifications = Notification.objects.filter(recipient=current_user).select_related('actor')[:20]
    
    return [
        NotificationResponse(
            id=n.id,
            message=n.message,
            link=n.link,
            actor=n.actor.username,
            is_read=n.is_read,
            created_at=n.created_at
        ) for n in notifications
    ]


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, current_user: User = Depends(get_current_user)):
    """Mark a notification as read."""
    from notifications.models import Notification
    try:
        notification = Notification.objects.get(id=notification_id, recipient=current_user)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return {"status": "success"}
    except Notification.DoesNotExist:
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
