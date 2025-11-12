"""Notification REST API routes"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.api.models.notification import (
    NotificationResponse,
    NotificationCreate,
    NotificationUpdate,
    NotificationListResponse
)
from backend.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])

# Global service instance (in production, use dependency injection)
notification_service = NotificationService()


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    limit: Optional[int] = Query(None, ge=1, le=100),
    unread_only: bool = Query(False)
):
    """Get all notifications"""
    notifications = notification_service.get_all_notifications(limit=limit, unread_only=unread_only)
    
    # Convert to response models
    notification_responses = [NotificationResponse(**n.to_dict()) for n in notifications]
    
    # Count unread
    all_notifications = notification_service.get_all_notifications()
    unread_count = sum(1 for n in all_notifications if not n.read)
    
    return NotificationListResponse(
        notifications=notification_responses,
        total=len(all_notifications),
        unread_count=unread_count
    )


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(notification_id: str):
    """Get a specific notification"""
    notification = notification_service.get_notification(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return NotificationResponse(**notification.to_dict())


@router.post("/", response_model=NotificationResponse, status_code=201)
async def create_notification(notification_data: NotificationCreate):
    """Create a new notification"""
    try:
        notification = notification_service.create_notification(
            notification_type=notification_data.type,
            priority=notification_data.priority,
            title=notification_data.title,
            message=notification_data.message,
            source=notification_data.source,
            symbol=notification_data.symbol,
            confidence_score=notification_data.confidence_score,
            urgency_score=notification_data.urgency_score,
            promise_score=notification_data.promise_score,
            metadata=notification_data.metadata,
            actions=notification_data.actions,
            expires_at=notification_data.expires_at
        )
        
        # Broadcast to WebSocket clients
        await notification_service.broadcast_notification(notification)
        
        return NotificationResponse(**notification.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{notification_id}", response_model=NotificationResponse)
async def update_notification(notification_id: str, update_data: NotificationUpdate):
    """Update a notification (mark as read, respond, etc.)"""
    notification = notification_service.get_notification(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Mark as read if requested
    if update_data.read is not None and update_data.read:
        notification = notification_service.mark_as_read(notification_id)
    
    # Record response if action provided
    if update_data.response_action:
        notification = notification_service.respond_to_notification(
            notification_id,
            update_data.response_action
        )
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return NotificationResponse(**notification.to_dict())


@router.post("/{notification_id}/respond")
async def respond_to_notification(
    notification_id: str,
    action: str = Query(..., description="Action: approve, reject, custom, snooze"),
    custom_message: Optional[str] = Query(None)
):
    """Respond to a notification"""
    notification = notification_service.respond_to_notification(
        notification_id,
        action,
        custom_message
    )
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return NotificationResponse(**notification.to_dict())


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(notification_id: str):
    """Delete a notification"""
    success = notification_service.delete_notification(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return None


@router.get("/stats/summary")
async def get_stats():
    """Get notification statistics"""
    stats = notification_service.get_stats()
    return stats

