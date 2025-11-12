"""Adapter to unify API client and direct NotificationManager usage"""

from typing import List, Optional, Dict
from src.monitoring.api_client import NotificationAPIClient
from src.notifications.notification_manager import NotificationManager
from src.notifications.notification_types import Notification, NotificationType, NotificationPriority, NotificationSource


class NotificationAdapter:
    """Adapter that works with either API client or direct NotificationManager"""
    
    def __init__(self, api_client: NotificationAPIClient, direct_manager: Optional[NotificationManager] = None):
        """
        Initialize adapter.
        
        Args:
            api_client: API client instance
            direct_manager: Direct NotificationManager (fallback)
        """
        self.api_client = api_client
        self.direct_manager = direct_manager
        self._use_api = None  # Will be determined on first use
    
    def _should_use_api(self) -> bool:
        """Determine if we should use API or direct manager"""
        if self._use_api is None:
            # Check API health on first use
            self._use_api = self.api_client.health_check()
        return self._use_api
    
    def get_all(self, limit: Optional[int] = None, unread_only: bool = False) -> List[Notification]:
        """Get all notifications"""
        if self._should_use_api():
            # Use API - convert dict responses to Notification objects
            notifications_data = self.api_client.get_notifications(limit=limit, unread_only=unread_only)
            return [self._dict_to_notification(n) for n in notifications_data]
        elif self.direct_manager:
            # Use direct manager
            return self.direct_manager.get_all(limit=limit, unread_only=unread_only)
        else:
            return []
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a specific notification"""
        if self._should_use_api():
            notification_data = self.api_client.get_notification(notification_id)
            if notification_data:
                return self._dict_to_notification(notification_data)
            return None
        elif self.direct_manager:
            all_notifications = self.direct_manager.get_all()
            for notification in all_notifications:
                if notification.notification_id == notification_id:
                    return notification
            return None
        else:
            return None
    
    def mark_as_read(self, notification_id: str):
        """Mark notification as read"""
        if self._should_use_api():
            self.api_client.mark_as_read(notification_id)
        elif self.direct_manager:
            self.direct_manager.mark_read(notification_id)
    
    def respond(self, notification_id: str, action: str, metadata: Optional[Dict] = None):
        """Respond to a notification"""
        if self._should_use_api():
            custom_message = metadata.get("custom_message") if metadata else None
            self.api_client.respond_to_notification(notification_id, action, custom_message)
        elif self.direct_manager:
            self.direct_manager.respond(notification_id, action, metadata)
    
    def get_system_status(self) -> Dict:
        """Get system status"""
        if self._should_use_api():
            # Calculate status from API data
            notifications = self.get_all()
            unread_count = sum(1 for n in notifications if not n.read)
            critical_count = sum(1 for n in notifications if n.priority == NotificationPriority.CRITICAL)
            high_count = sum(1 for n in notifications if n.priority == NotificationPriority.HIGH)
            
            if critical_count > 0:
                status = "critical"
                message = f"⚠️ {critical_count} critical alert(s) require attention"
            elif high_count > 0:
                status = "attention"
                message = f"📊 {high_count} high-priority opportunity(ies) available"
            elif unread_count > 0:
                status = "active"
                message = f"✅ {unread_count} notification(s) - All systems normal"
            else:
                status = "ok"
                message = "✅ All systems normal - Monitoring active"
            
            return {
                'status': status,
                'message': message,
                'unread_count': unread_count,
                'critical_count': critical_count,
                'high_count': high_count,
                'total_notifications': len(notifications)
            }
        elif self.direct_manager:
            return self.direct_manager.get_system_status()
        else:
            return {
                'status': 'ok',
                'message': '✅ All systems normal - Monitoring active',
                'unread_count': 0,
                'critical_count': 0,
                'high_count': 0,
                'total_notifications': 0
            }
    
    def notify(
        self,
        notification_type: NotificationType,
        priority: NotificationPriority,
        title: str,
        message: str,
        source: NotificationSource,
        symbol: Optional[str] = None,
        confidence_score: Optional[float] = None,
        urgency_score: Optional[float] = None,
        promise_score: Optional[float] = None,
        metadata: Optional[Dict] = None,
        actions: Optional[List[str]] = None
    ) -> Notification:
        """Create a new notification"""
        if self._should_use_api():
            # Use API
            notification_data = self.api_client.create_notification(
                notification_type=notification_type.value,
                priority=priority.value,
                title=title,
                message=message,
                source=source.value,
                symbol=symbol,
                confidence_score=confidence_score,
                urgency_score=urgency_score,
                promise_score=promise_score,
                metadata=metadata,
                actions=actions
            )
            if notification_data:
                return self._dict_to_notification(notification_data)
            # If API call failed, fall back to direct manager
            if self.direct_manager:
                return self.direct_manager.notify(
                    notification_type, priority, title, message, source,
                    symbol, confidence_score, urgency_score, promise_score,
                    metadata, actions
                )
        elif self.direct_manager:
            # Use direct manager
            return self.direct_manager.notify(
                notification_type, priority, title, message, source,
                symbol, confidence_score, urgency_score, promise_score,
                metadata, actions
            )
        
        # Fallback: create minimal notification
        from datetime import datetime
        import uuid
        notification = Notification(
            notification_id=str(uuid.uuid4())[:8],
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            source=source,
            symbol=symbol,
            confidence_score=confidence_score,
            urgency_score=urgency_score,
            promise_score=promise_score,
            metadata=metadata or {},
            actions=actions or []
        )
        return notification
    
    def _dict_to_notification(self, data: Dict) -> Notification:
        """Convert API response dict to Notification object"""
        # Parse created_at
        from datetime import datetime
        created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        
        # Parse expires_at if present
        expires_at = None
        if data.get('expires_at'):
            expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        
        # Parse response_at if present
        response_at = None
        if data.get('response_at'):
            response_at = datetime.fromisoformat(data['response_at'].replace('Z', '+00:00'))
        
        # Create Notification object
        notification = Notification(
            notification_id=data['id'],
            notification_type=NotificationType(data['type']),
            priority=NotificationPriority(data['priority']),
            title=data['title'],
            message=data['message'],
            source=NotificationSource(data['source']),
            symbol=data.get('symbol'),
            confidence_score=data.get('confidence_score'),
            urgency_score=data.get('urgency_score'),
            promise_score=data.get('promise_score'),
            metadata=data.get('metadata', {}),
            actions=data.get('actions', []),
            expires_at=expires_at
        )
        
        # Set additional attributes
        notification.created_at = created_at
        notification.read = data.get('read', False)
        notification.responded = data.get('responded', False)
        notification.response_action = data.get('response_action')
        notification.response_at = response_at
        
        return notification

