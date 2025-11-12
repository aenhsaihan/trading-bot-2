"""Notification service - wraps NotificationManager for API"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.notifications.notification_manager import NotificationManager
from src.notifications.notification_types import (
    NotificationType,
    NotificationPriority,
    NotificationSource
)
from typing import List, Optional, Dict
from datetime import datetime


class NotificationService:
    """Service layer for notifications API"""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize notification service"""
        self.manager = NotificationManager(config)
        self._websocket_clients: List = []  # Will store WebSocket connections
    
    def add_websocket_client(self, websocket):
        """Add a WebSocket client for real-time updates"""
        self._websocket_clients.append(websocket)
    
    def remove_websocket_client(self, websocket):
        """Remove a WebSocket client"""
        if websocket in self._websocket_clients:
            self._websocket_clients.remove(websocket)
    
    async def broadcast_notification(self, notification):
        """Broadcast notification to all WebSocket clients"""
        if not self._websocket_clients:
            return
        
        notification_dict = notification.to_dict()
        
        # Send to all connected clients
        disconnected = []
        for client in self._websocket_clients:
            try:
                await client.send_json(notification_dict)
            except Exception as e:
                # Client disconnected, mark for removal
                disconnected.append(client)
        
        # Remove disconnected clients
        for client in disconnected:
            self.remove_websocket_client(client)
    
    def create_notification(
        self,
        notification_type: str,
        priority: str,
        title: str,
        message: str,
        source: str,
        symbol: Optional[str] = None,
        confidence_score: Optional[float] = None,
        urgency_score: Optional[float] = None,
        promise_score: Optional[float] = None,
        metadata: Optional[Dict] = None,
        actions: Optional[List[str]] = None,
        expires_at: Optional[str] = None
    ):
        """Create a new notification"""
        # Convert string enums to enum types
        try:
            notif_type = NotificationType(notification_type)
            notif_priority = NotificationPriority(priority)
            notif_source = NotificationSource(source)
        except ValueError as e:
            raise ValueError(f"Invalid enum value: {e}")
        
        # Parse expires_at if provided
        expires_dt = None
        if expires_at:
            try:
                expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            except ValueError:
                pass
        
        # Create notification
        notification = self.manager.notify(
            notification_type=notif_type,
            priority=notif_priority,
            title=title,
            message=message,
            source=notif_source,
            symbol=symbol,
            confidence_score=confidence_score,
            urgency_score=urgency_score,
            promise_score=promise_score,
            metadata=metadata or {},
            actions=actions or [],
            expires_at=expires_dt
        )
        
        return notification
    
    def get_all_notifications(self, limit: Optional[int] = None, unread_only: bool = False) -> List:
        """Get all notifications"""
        notifications = self.manager.get_all()
        
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        
        if limit:
            notifications = notifications[:limit]
        
        return notifications
    
    def get_notification(self, notification_id: str):
        """Get a specific notification"""
        all_notifications = self.manager.get_all()
        for notification in all_notifications:
            if notification.notification_id == notification_id:
                return notification
        return None
    
    def mark_as_read(self, notification_id: str):
        """Mark notification as read"""
        notification = self.get_notification(notification_id)
        if notification:
            self.manager.mark_read(notification_id)
            # Return updated notification
            return self.get_notification(notification_id)
        return None
    
    def respond_to_notification(self, notification_id: str, action: str, custom_message: Optional[str] = None):
        """Respond to a notification"""
        notification = self.get_notification(notification_id)
        if notification:
            # Use respond method (which exists) instead of record_response
            metadata = {"custom_message": custom_message} if custom_message else None
            self.manager.respond(notification_id, action, metadata)
            # Return updated notification
            return self.get_notification(notification_id)
        return None
    
    def delete_notification(self, notification_id: str):
        """Delete a notification (remove from history)"""
        # Note: This would need to be added to NotificationManager
        # For now, we'll just mark as responded
        notification = self.get_notification(notification_id)
        if notification:
            self.manager.record_response(notification_id, "dismissed")
            return True
        return False
    
    def get_stats(self) -> Dict:
        """Get notification statistics"""
        return self.manager.get_stats()

