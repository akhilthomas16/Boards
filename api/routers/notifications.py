"""
Notifications router — handles WebSockets and notification CRUD.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
import asyncio
import redis.asyncio as aioredis
from django.conf import settings
from pydantic import BaseModel
from typing import List
from datetime import datetime
import json

from ..auth import verify_token, get_current_user
from django.contrib.auth.models import User

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
async def websocket_notifications(websocket: WebSocket, token: str):
    """
    WebSocket endpoint for real-time notifications.
    Client connects with: wss://api/ws?token=<jwt>
    """
    await websocket.accept()
    pubsub = None
    r = None
    
    try:
        # Authenticate token manually (cannot use standard Depends in WS easily without throwing 403 on handshake)
        payload = verify_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            await websocket.close(code=1008)
            return
            
        # Connect to Redis asynchronously
        r = aioredis.from_url(settings.CACHES['default']['LOCATION'])
        pubsub = r.pubsub()
        channel_name = f"user_{user_id}_notifications"
        await pubsub.subscribe(channel_name)
        
        # Listen for messages
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"].decode("utf-8")
                await websocket.send_text(data)
                
    except Exception as e:
        print(f"WebSocket disconnected or error: {e}")
        try:
            await websocket.close(code=1008)
        except:
            pass
    finally:
        # Cleanup Pub/Sub
        if pubsub:
            await pubsub.unsubscribe(channel_name)
            await pubsub.close()
        if r:
            await r.aclose()
