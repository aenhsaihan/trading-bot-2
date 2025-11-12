"""Central notification manager"""

import uuid
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from .notification_queue import NotificationQueue
from .notification_types import (
    Notification,
    NotificationType,
    NotificationPriority,
    NotificationSource
)
from src.utils.logger import setup_logger


class NotificationManager:
    """Central hub for managing all notifications"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize notification manager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.queue = NotificationQueue()
        self.history: List[Notification] = []  # Store notification history
        self.callbacks: List[Callable] = []  # Callbacks for new notifications
        self.logger = setup_logger(f"{__name__}.NotificationManager")
        
        # Notification preferences
        self.preferences = self.config.get('notification_preferences', {})
        self.autonomy_config = self.config.get('autonomy_config', {})
        
        # Statistics
        self.stats = {
            'total_notifications': 0,
            'by_priority': {},
            'by_type': {},
            'by_source': {},
            'autonomous_actions': 0,
            'user_responses': 0
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
        actions: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None
    ) -> Notification:
        """
        Create and queue a new notification.
        
        Args:
            notification_type: Type of notification
            priority: Priority level
            title: Notification title
            message: Detailed message
            source: Source of notification
            symbol: Trading pair symbol
            confidence_score: Confidence score (0-100)
            urgency_score: Urgency score (0-100)
            promise_score: Promise score (0-100)
            metadata: Additional data
            actions: Available actions
            expires_at: Expiration time
            
        Returns:
            Created notification
        """
        notification_id = str(uuid.uuid4())[:8]
        
        notification = Notification(
            notification_id=notification_id,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            source=source,
            symbol=symbol,
            confidence_score=confidence_score,
            urgency_score=urgency_score,
            promise_score=promise_score,
            metadata=metadata,
            actions=actions,
            expires_at=expires_at
        )
        
        # Add to queue
        self.queue.add(notification)
        
        # Add to history
        self.history.append(notification)
        if len(self.history) > 1000:  # Keep last 1000 notifications
            self.history = self.history[-1000:]
        
        # Update statistics
        self._update_stats(notification)
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(notification)
            except Exception as e:
                self.logger.error(f"Error in notification callback: {e}")
        
        self.logger.info(f"Notification created: {title} ({priority.value})")
        
        return notification
    
    def get_next(self) -> Optional[Notification]:
        """Get next highest priority notification"""
        return self.queue.pop()
    
    def get_all(self, limit: Optional[int] = None, unread_only: bool = False) -> List[Notification]:
        """
        Get all notifications.
        
        Args:
            limit: Maximum number to return
            unread_only: Only return unread notifications
            
        Returns:
            List of notifications
        """
        if unread_only:
            notifications = self.queue.get_unread()
        else:
            notifications = self.queue.get_all(limit=limit)
        
        return notifications
    
    def get_by_priority(self, priority: NotificationPriority) -> List[Notification]:
        """Get notifications by priority"""
        return self.queue.get_by_priority(priority)
    
    def mark_read(self, notification_id: str):
        """Mark notification as read"""
        self.queue.mark_read(notification_id)
        # Also update in history
        for notif in self.history:
            if notif.notification_id == notification_id:
                notif.read = True
                break
    
    def respond(
        self,
        notification_id: str,
        action: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Record user response to notification.
        
        Args:
            notification_id: Notification ID
            action: Action taken (e.g., "approve", "reject", "custom")
            metadata: Additional response metadata
            
        Returns:
            True if response recorded
        """
        notification = None
        for notif in self.history:
            if notif.notification_id == notification_id:
                notification = notif
                break
        
        if not notification:
            return False
        
        notification.responded = True
        notification.response_action = action
        notification.response_at = datetime.now()
        notification.metadata['response_metadata'] = metadata or {}
        
        self.stats['user_responses'] += 1
        
        self.logger.info(f"User responded to {notification_id}: {action}")
        
        return True
    
    def register_callback(self, callback: Callable):
        """Register callback for new notifications"""
        self.callbacks.append(callback)
    
    def get_system_status(self) -> Dict:
        """
        Get system status for "Everything OK" indicator.
        
        Returns:
            Status dictionary
        """
        unread_count = len(self.queue.get_unread())
        critical_count = len(self.queue.get_by_priority(NotificationPriority.CRITICAL))
        high_count = len(self.queue.get_by_priority(NotificationPriority.HIGH))
        
        # Determine overall status
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
            'total_notifications': self.stats['total_notifications']
        }
    
    def _update_stats(self, notification: Notification):
        """Update statistics"""
        self.stats['total_notifications'] += 1
        
        # By priority
        priority_key = notification.priority.value
        self.stats['by_priority'][priority_key] = self.stats['by_priority'].get(priority_key, 0) + 1
        
        # By type
        type_key = notification.notification_type.value
        self.stats['by_type'][type_key] = self.stats['by_type'].get(type_key, 0) + 1
        
        # By source
        source_key = notification.source.value
        self.stats['by_source'][source_key] = self.stats['by_source'].get(source_key, 0) + 1
    
    def get_stats(self) -> Dict:
        """Get notification statistics"""
        return self.stats.copy()

