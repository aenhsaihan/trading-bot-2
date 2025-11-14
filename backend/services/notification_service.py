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
from backend.services.notification_message_service import NotificationMessageService
from typing import List, Optional, Dict
from datetime import datetime


class NotificationService:
    """Service layer for notifications API"""
    
    # Singleton instance
    _instance = None
    _websocket_clients: List = []  # Shared across all instances
    
    def __new__(cls, config: Optional[Dict] = None):
        """Singleton pattern - ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(NotificationService, cls).__new__(cls)
            cls._instance.manager = NotificationManager(config)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize notification service (only once)"""
        if self._initialized:
            return
        self._initialized = True
        # _websocket_clients is a class variable, shared across instances
        # Initialize message summarization service
        self.message_service = NotificationMessageService()
    
    def add_websocket_client(self, websocket):
        """Add a WebSocket client for real-time updates"""
        if websocket not in NotificationService._websocket_clients:
            NotificationService._websocket_clients.append(websocket)
            print(f"[NotificationService] WebSocket client added. Total clients: {len(NotificationService._websocket_clients)}")
    
    def remove_websocket_client(self, websocket):
        """Remove a WebSocket client"""
        if websocket in NotificationService._websocket_clients:
            NotificationService._websocket_clients.remove(websocket)
            print(f"[NotificationService] WebSocket client removed. Total clients: {len(NotificationService._websocket_clients)}")
    
    async def broadcast_notification(self, notification):
        """Broadcast notification to all WebSocket clients"""
        if not NotificationService._websocket_clients:
            print("[NotificationService] No WebSocket clients connected, skipping broadcast")
            return
        
        notification_dict = notification.to_dict()
        print(f"[NotificationService] Broadcasting notification to {len(NotificationService._websocket_clients)} client(s): {notification_dict.get('title', 'N/A')}")
        
        # Send to all connected clients
        disconnected = []
        for client in NotificationService._websocket_clients:
            try:
                await client.send_json(notification_dict)
                print(f"[NotificationService] Sent notification to client successfully")
            except Exception as e:
                # Client disconnected, mark for removal
                print(f"[NotificationService] Error sending to client: {e}")
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
        
        # Generate AI-summarized message (StarCraft-style)
        try:
            notification_dict = notification.to_dict()
            summarized = self.message_service.summarize(notification_dict)
            notification.summarized_message = summarized
        except Exception as e:
            # Log error but don't fail notification creation
            import traceback
            print(f"[NotificationService] Error generating summary: {e}")
            print(traceback.format_exc())
            # Fallback: use title as summary
            notification.summarized_message = title
        
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

